"""
Résolution d'URLs embed en URLs de stream directes.

Utilisé par le plugin Jellyfin pour obtenir une URL lisible directement
sans avoir à télécharger le fichier.

  GET /api/stream/resolve?url=<embed_url>
    → { url, audio_url, ext, protocol, headers, title, duration, merged }

Authentification requise (Bearer token utilisateur, admin ou client API).
La résolution passe par yt-dlp dans un thread pool — compter 2-8 s selon la source.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_current_user
from services import downloader

router = APIRouter(prefix="/api/stream", tags=["Stream"])


@router.get(
    "/resolve",
    summary="Résout une URL embed en URL de stream directe",
    response_description=(
        "url (str) — URL directe du flux vidéo\n"
        "audio_url (str|null) — URL audio séparée si les flux sont séparés\n"
        "ext (str) — extension (mp4, m3u8…)\n"
        "protocol (str) — https, m3u8, m3u8_native…\n"
        "headers (dict) — headers HTTP requis pour lire le flux (Referer, Origin…)\n"
        "title (str) — titre extrait par yt-dlp\n"
        "duration (int|null) — durée en secondes\n"
        "merged (bool) — true si vidéo et audio sont sur des URLs séparées"
    ),
)
async def resolve_stream(
    url: str = Query(..., description="URL embed à résoudre (ex: https://sibnet.ru/shell.php?videoid=xxx)"),
    _: dict = Depends(get_current_user),
):
    try:
        result = await asyncio.wait_for(
            downloader.resolve_stream_url(url),
            timeout=30.0,
        )
        return result
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
