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
from urllib.parse import urlencode, urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer

from api.dependencies import get_current_user, oauth2_scheme, _validate_token, _enrich_user
from services import downloader

router = APIRouter(prefix="/api/stream", tags=["Stream"])

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


def _build_proxy_path(target: str, referer: Optional[str], ua: Optional[str], token: str) -> str:
    params = {"url": target, "token": token}
    if referer:
        params["referer"] = referer
    if ua:
        params["ua"] = ua
    return "/api/stream/proxy?" + urlencode(params)


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


def _rewrite_m3u8(text: str, manifest_url: str, referer: Optional[str], ua: Optional[str], token: str) -> str:
    """Réécrit un manifest HLS pour que chaque segment/clé/sous-playlist repasse par /proxy."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        if stripped.startswith("#EXT-X-KEY") or stripped.startswith("#EXT-X-MAP"):
            m = re.search(r'URI="([^"]+)"', stripped)
            if m:
                abs_url = urljoin(manifest_url, m.group(1))
                proxied = _build_proxy_path(abs_url, referer, ua, token)
                stripped = stripped.replace(m.group(1), proxied)
            out.append(stripped)
            continue
        if stripped.startswith("#"):
            out.append(line)
            continue
        # Ligne d'URL : segment .ts ou sous-playlist (variant HLS)
        abs_url = urljoin(manifest_url, stripped)
        out.append(_build_proxy_path(abs_url, referer, ua, token))
    return "\n".join(out)


@router.get(
    "/proxy",
    summary="Relaie un flux vidéo/HLS en réinjectant les headers requis (Referer/User-Agent)",
)
async def proxy_stream(
    request: Request,
    url:     str = Query(..., description="URL directe à relayer"),
    referer: Optional[str] = Query(None),
    ua:      Optional[str] = Query(None),
    token:   Optional[str] = Query(None, description="Requis pour que les segments HLS réécrits restent authentifiés"),
    user:    dict = Depends(_get_stream_user),
):
    upstream_headers: dict = {}
    if referer:
        upstream_headers["Referer"] = referer
    if ua:
        upstream_headers["User-Agent"] = ua
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
    try:
        req = client.build_request("GET", url, headers=upstream_headers)
        upstream = await client.send(req, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Erreur en amont : {exc}")

    content_type = upstream.headers.get("content-type", "")
    is_manifest = url.split("?")[0].lower().endswith(".m3u8") or "mpegurl" in content_type

    if is_manifest:
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        text = body.decode("utf-8", errors="ignore")
        rewritten = _rewrite_m3u8(text, url, referer, ua, token or "")
        return Response(content=rewritten, media_type="application/vnd.apple.mpegurl")

    async def _iter_body():
        try:
            async for chunk in upstream.aiter_bytes(65536):
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

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
