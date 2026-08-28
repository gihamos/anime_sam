"""
Résolution d'URLs embed en URLs de stream directes, + relais HTTP (proxy) de
ces flux pour les lecteurs qui ne propagent pas correctement les headers
personnalisés (Referer/User-Agent) — notamment les segments HLS individuels,
et n'importe quel lecteur externe (VLC, MX Player…) qui ne peut pas du tout
envoyer de headers custom.

  GET /api/stream/resolve?url=<embed_url>
    → { url, proxy_url, audio_url, ext, protocol, headers, title, duration, merged }

  GET /api/stream/proxy?url=<direct_url>&referer=...&ua=...&token=...
    → relaie le flux (ou le manifest HLS, réécrit pour que chaque segment
      repasse aussi par ce proxy) en réinjectant les headers requis.

Authentification :
  /resolve → Bearer token (header)
  /proxy   → Bearer token OU ?token=... (les lecteurs vidéo ne peuvent pas
             tous envoyer de header Authorization personnalisé)

La résolution passe par yt-dlp dans un thread pool — compter 2-8 s selon la source.
"""

import asyncio
import re
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer

from api.dependencies import get_current_user, oauth2_scheme, _validate_token, _enrich_user
from services import downloader

router = APIRouter(prefix="/api/stream", tags=["Stream"])

# Client HTTP partagé pour /proxy — un épisode HLS peut représenter des centaines de
# segments, et ouvrir un httpx.AsyncClient() par requête (comme avant) rouvre une connexion
# TCP+TLS neuve à chaque segment au lieu de réutiliser une connexion déjà établie vers le
# même hôte (keep-alive). Constaté en conditions réelles : des segments qui devraient se
# récupérer en < 1 s prenaient 5-15 s, avec des redémarrages complets du flux (Jellyfin
# rejouant le manifest depuis le début) toutes les quelques minutes — cohérent avec des
# connexions lentes/instables plutôt qu'un vrai problème de source. Un client unique, créé
# au démarrage de l'app et fermé à l'arrêt (voir init_client/close_client, câblés dans
# main.py), garde un pool de connexions persistantes par hôte.
_client: Optional[httpx.AsyncClient] = None


def init_client() -> None:
    global _client
    _client = httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50, keepalive_expiry=30.0),
    )


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

# ── Auth pour /proxy : header Bearer OU ?token= (requis pour les lecteurs vidéo) ──

_oauth2_optional_query = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _get_stream_user(
    bearer: Optional[str] = Depends(_oauth2_optional_query),
    token:  Optional[str] = Query(None, alias="token"),
) -> dict:
    t = token or bearer
    if not t:
        raise HTTPException(401, "Token d'authentification requis")
    user = await _validate_token(t)
    return await _enrich_user(user)


# Extensions que le démuxeur HLS d'ffmpeg accepte pour les ressources imbriquées
# (segments, sous-playlists, pistes alternatives) — passé ce point c'est une liste de sécurité
# fermée côté ffmpeg (anti confusion de protocole), pas configurable depuis notre côté.
_KNOWN_HLS_EXTENSIONS = {
    ".ts", ".m4s", ".m4a", ".m4v", ".mp4", ".aac", ".m3u8", ".vtt", ".webvtt", ".key",
}


def _sniff_extension(target: str) -> str:
    """Extension réelle de `target` si elle est reconnue par ffmpeg, sinon `.ts` par défaut
    (le cas le plus courant pour un segment vidéo)."""
    path = urlparse(target).path
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    return ext if ext in _KNOWN_HLS_EXTENSIONS else ".ts"


def _build_proxy_path(target: str, referer: Optional[str], ua: Optional[str], token: str) -> str:
    """
    Construit l'URL de notre proxy pour `target`. Le vrai flux à relayer voyage dans le
    paramètre `url=` — mais le démuxeur HLS d'ffmpeg (utilisé par Jellyfin) rejette toute
    ressource imbriquée dont le CHEMIN de l'URL n'expose pas une extension reconnue
    ("... is not in allowed_segment_extensions"), même si le vrai flux en a une, planquée
    dans la query string. On ajoute donc un nom de fichier cosmétique reprenant l'extension
    réelle de `target` dans notre propre chemin, pour satisfaire ce sniffing.
    """
    params = {"url": target, "token": token}
    if referer:
        params["referer"] = referer
    if ua:
        params["ua"] = ua
    return f"/api/stream/proxy/seg{_sniff_extension(target)}?" + urlencode(params)


@router.get(
    "/resolve",
    summary="Résout une URL embed en URL de stream directe",
    response_description=(
        "url (str) — URL directe du flux vidéo (CDN d'origine)\n"
        "proxy_url (str|null) — URL relative, à travers notre serveur, avec headers déjà injectés "
        "— à préférer pour la lecture (fonctionne avec n'importe quel lecteur, interne ou externe)\n"
        "audio_url (str|null) — URL audio séparée si les flux sont séparés\n"
        "ext (str) — extension (mp4, m3u8…)\n"
        "protocol (str) — https, m3u8, m3u8_native…\n"
        "headers (dict) — headers HTTP requis pour lire le flux directement (Referer, Origin…)\n"
        "title (str) — titre extrait par yt-dlp\n"
        "duration (int|null) — durée en secondes\n"
        "merged (bool) — true si vidéo et audio sont sur des URLs séparées"
    ),
)
async def resolve_stream(
    url:   str = Query(..., description="URL embed à résoudre (ex: https://sibnet.ru/shell.php?videoid=xxx)"),
    _:     dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    try:
        result = await asyncio.wait_for(
            downloader.resolve_stream_url(url),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Délai dépassé — la source n'a pas répondu dans les 30 s",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la résolution : {exc}",
        )

    proxy_url = None
    if result.get("url") and not result.get("merged"):
        headers = result.get("headers") or {}
        proxy_url = _build_proxy_path(
            result["url"], headers.get("Referer"), headers.get("User-Agent"), token
        )
    result["proxy_url"] = proxy_url
    return result


_URI_ATTR = re.compile(r'URI="([^"]+)"')


def _rewrite_m3u8(text: str, manifest_url: str, referer: Optional[str], ua: Optional[str], token: str) -> str:
    """
    Réécrit un manifest HLS pour que chaque segment/clé/sous-playlist/piste alternative
    repasse par /proxy.

    N'importe quelle balise HLS peut porter un attribut URI="…" — pas seulement
    EXT-X-KEY/EXT-X-MAP : Vidzy utilise EXT-X-MEDIA pour ses pistes audio alternatives
    (français/anglais), qui n'étaient pas réécrites ici (seuls EXT-X-KEY/EXT-X-MAP
    l'étaient), donc ffmpeg tentait de les récupérer en URL relative brute — 404 côté
    lecteur ("Erreur de lecture"). On traite maintenant génériquement toute balise
    commentaire contenant URI="…", ce qui couvre aussi EXT-X-I-FRAME-STREAM-INF et
    consorts sans avoir à lister chaque balise HLS existante ou future.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        if stripped.startswith("#"):
            if 'URI="' in stripped:
                def _replace(m: "re.Match[str]") -> str:
                    abs_url = urljoin(manifest_url, m.group(1))
                    return f'URI="{_build_proxy_path(abs_url, referer, ua, token)}"'
                stripped = _URI_ATTR.sub(_replace, stripped)
            out.append(stripped)
            continue
        # Ligne d'URL : segment .ts ou sous-playlist (variant HLS)
        abs_url = urljoin(manifest_url, stripped)
        out.append(_build_proxy_path(abs_url, referer, ua, token))
    return "\n".join(out)


async def _fetch_with_retry(
    client: httpx.AsyncClient, url: str, headers: dict, retries: int = 2, delay: float = 0.7,
) -> httpx.Response:
    """
    GET avec quelques tentatives en cas d'échec HTTP (pas d'exception réseau, qui remonte
    directement) — certaines CDN de lecteurs (vu en conditions réelles sur Vidzy) répondent
    parfois 403/404 juste après la résolution du manifest signé, avant de redevenir correctes
    quelques centaines de ms plus tard (propagation entre nœuds edge probable).
    """
    upstream: Optional[httpx.Response] = None
    for attempt in range(retries + 1):
        req = client.build_request("GET", url, headers=headers)
        upstream = await client.send(req, stream=True)
        if upstream.is_success or attempt == retries:
            return upstream
        await upstream.aclose()
        await asyncio.sleep(delay)
    return upstream  # pragma: no cover — boucle toujours au moins une itération


@router.get(
    "/proxy",
    summary="Relaie un flux vidéo/HLS en réinjectant les headers requis (Referer/User-Agent)",
)
@router.get(
    "/proxy/{filename}",
    include_in_schema=False,
    summary="Identique à /proxy — chemin avec extension cosmétique pour le sniffing ffmpeg",
)
async def proxy_stream(
    request:  Request,
    url:      str = Query(..., description="URL directe à relayer"),
    referer:  Optional[str] = Query(None),
    ua:       Optional[str] = Query(None),
    token:    Optional[str] = Query(None, description="Requis pour que les segments HLS réécrits restent authentifiés"),
    filename: str = "seg.ts",  # non utilisé — voir _build_proxy_path
    user:     dict = Depends(_get_stream_user),
):
    upstream_headers: dict = {}
    if referer:
        upstream_headers["Referer"] = referer
    if ua:
        upstream_headers["User-Agent"] = ua
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    assert _client is not None, "init_client() doit être appelé au démarrage de l'app"
    try:
        upstream = await _fetch_with_retry(_client, url, upstream_headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur en amont : {exc}")

    content_type = upstream.headers.get("content-type", "")
    # Certains CDN (vu en conditions réelles sur Vidzy) renvoient parfois une erreur HTTP
    # (403/404, page HTML nginx) juste après la résolution du manifest signé — flaky, sans
    # doute une histoire de propagation entre nœuds edge. Un manifest n'est traité comme tel
    # que si la requête a réellement réussi ; sinon on relaie l'erreur telle quelle plutôt que
    # de réécrire la page d'erreur HTML comme si c'était une playlist HLS valide (ce qui
    # produisait un flux qui semblait correct syntaxiquement mais ne jouait jamais).
    is_manifest = upstream.is_success and (
        url.split("?")[0].lower().endswith(".m3u8") or "mpegurl" in content_type
    )

    if is_manifest:
        body = await upstream.aread()
        await upstream.aclose()
        text = body.decode("utf-8", errors="ignore")
        rewritten = _rewrite_m3u8(text, url, referer, ua, token or "")
        return Response(content=rewritten, media_type="application/vnd.apple.mpegurl")

    async def _iter_body():
        try:
            async for chunk in upstream.aiter_bytes(65536):
                yield chunk
        finally:
            await upstream.aclose()

    passthrough_headers = {}
    for h in ("content-length", "content-range", "accept-ranges", "content-type"):
        if h in upstream.headers:
            passthrough_headers[h] = upstream.headers[h]

    return StreamingResponse(
        _iter_body(),
        status_code=upstream.status_code,
        headers=passthrough_headers,
        media_type=content_type or "application/octet-stream",
    )
