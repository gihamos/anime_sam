"""
Téléchargement de vidéos via yt-dlp.

yt-dlp gère nativement : cookies, headers de session, HLS/DASH, merge audio+vidéo.
On ne tente PAS de proxifier l'URL directe via httpx — c'est non fiable
(sessions expirées, manifests HLS, DRM partiel, headers manquants).

API publique :
  download_to_file(player_url, dest, stem, cancel, on_progress) → Path | None
  build_zip(items, zip_path, on_progress, cancel, on_file_progress) → int

Annulation :
  Passer un threading.Event ; quand il est set(), le progress hook lève une
  exception qui interrompt yt-dlp proprement (y compris les téléchargements HLS).

Progression byte-level :
  `on_progress(downloaded, total, speed, eta)` callback sync appelé à chaque chunk.
  Utilisé pour afficher vitesse/ETA/octets dans l'UI.
"""

import asyncio
import re
import threading
import zipfile
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from utils.logger import logger

# ── Constantes ────────────────────────────────────────────────────────────────

_MAX_ITEMS_PER_ZIP = 50

_YDL_BASE = {
    "quiet":       True,
    "no_warnings": True,
    "geo_bypass":  True,
    "retries":          5,
    "fragment_retries": 5,
    "socket_timeout":   30,
}

_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"


# ── Helper synchrone (tourne dans un ThreadPoolExecutor) ─────────────────────

def _safe_stem(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', s).strip() or "video"


def _download_to_dir_sync(
    url:         str,
    dest:        Path,
    stem:        str,
    cancel:      Optional[threading.Event] = None,
    on_progress: Optional[Callable]        = None,
) -> Optional[Path]:
    """
    Télécharge la vidéo via yt-dlp dans `dest/stem.ext`.
    `cancel`      : threading.Event — coupe le téléchargement via le progress hook.
    `on_progress` : callable sync (downloaded, total, speed, eta) — appelé à chaque chunk.
    """
    safe     = _safe_stem(stem)
    out_tmpl = str(dest / f"{safe}.%(ext)s")

    def _progress_hook(d: dict) -> None:
        if cancel and cancel.is_set():
            raise Exception("_cancelled_")
        if on_progress and d.get("status") == "downloading":
            dl  = int(d.get("downloaded_bytes") or 0)
            tot = int(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
            spd = float(d.get("speed") or 0.0)
            eta = int(d.get("eta") or 0)
            on_progress(dl, tot, spd, eta)

    opts = {
        **_YDL_BASE,
        "format":              _FORMAT,
        "outtmpl":             out_tmpl,
        "merge_output_format": "mp4",
        "cookiefile":          None,
        "prefer_ffmpeg":       True,
        "progress_hooks":      [_progress_hook],
        "postprocessors": [{
            "key":             "FFmpegVideoConvertor",
            "preferedformat":  "mp4",
        }],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        for p in sorted(dest.glob(f"{safe}.*")):
            if p.stat().st_size > 0 and p.suffix not in (".part", ".ytdl"):
                logger.info(f"yt-dlp → {p.name} ({p.stat().st_size // 1024} Ko)")
                return p
    except yt_dlp.utils.DownloadError as exc:
        if cancel and cancel.is_set():
            logger.info(f"yt-dlp : annulé ({url[:80]})")
        else:
            logger.error(f"yt-dlp DownloadError: {exc!r} ({url[:80]})")
    except Exception as exc:
        if cancel and cancel.is_set():
            logger.info(f"yt-dlp : annulé ({url[:80]})")
        else:
            logger.error(f"yt-dlp error: {exc!r} ({url[:80]})")
    return None


# ── API publique asynchrone ───────────────────────────────────────────────────

async def download_to_file(
    player_url:  str | list[str],
    dest:        Path,
    stem:        str,
    cancel:      Optional[threading.Event] = None,
    on_progress: Optional[Callable]        = None,
) -> Optional[Path]:
    """
    Télécharge une vidéo sur disque via yt-dlp (async wrapper).

    `player_url` accepte une URL unique ou une liste d'URLs candidates
    (plusieurs lecteurs pour le même épisode) — la première qui aboutit
    est utilisée, les suivantes ne sont tentées qu'en cas d'échec.
    """
    urls = player_url if isinstance(player_url, list) else [player_url]
    loop = asyncio.get_running_loop()

    for i, url in enumerate(urls):
        if cancel and cancel.is_set():
            return None
        result = await loop.run_in_executor(
            None, _download_to_dir_sync, url, dest, stem, cancel, on_progress
        )
        if result is not None:
            return result
        if i < len(urls) - 1:
            logger.warning(f"download_to_file: source {i + 1}/{len(urls)} a échoué, tentative avec la suivante…")

    return None


def _resolve_sync(embed_url: str) -> dict:
    """Résout une URL embed en URL de stream directe via yt-dlp (sans télécharger)."""
    opts = {
        **_YDL_BASE,
        # On préfère un flux unique (vidéo + audio dans un seul fichier)
        # pour éviter d'avoir à merger côté Jellyfin
        "format": "best[ext=mp4]/best[ext=m3u8]/bestvideo[ext=mp4]+bestaudio/best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(embed_url, download=False)

    if not info:
        raise ValueError("Impossible d'extraire l'URL de stream")

    title    = info.get("title", "")
    duration = info.get("duration")

    def _pick_headers(d: dict) -> dict:
        raw = d.get("http_headers", {})
        # User-Agent inclus : de nombreux CDN valident le UA en plus du Referer sur
        # chaque requête de segment. Sans lui, le lecteur (UA par défaut ExoPlayer/
        # AVPlayer, différent de celui utilisé par yt-dlp pour résoudre) se prend un 403.
        keep = {"Referer", "Origin", "Cookie", "User-Agent"}
        return {k: v for k, v in raw.items() if k in keep}

    # ── Formats mergés (video + audio séparés) ─────────────────────────────────
    req = info.get("requested_formats")
    if req:
        video = next((f for f in req if f.get("vcodec", "none") != "none"), None)
        audio = next(
            (f for f in req if f.get("acodec", "none") != "none"
             and f.get("vcodec", "none") == "none"),
            None,
        )
        return {
            "url":       video["url"] if video else None,
            "audio_url": audio["url"] if audio else None,
            "ext":       video.get("ext", "mp4") if video else "mp4",
            "protocol":  video.get("protocol", "https") if video else "https",
            "headers":   _pick_headers(video) if video else {},
            "title":     title,
            "duration":  duration,
            "merged":    True,
        }

    # ── Flux unique (HLS, DASH, MP4 direct) ───────────────────────────────────
    url = info.get("url")
    if not url:
        raise ValueError("Aucune URL de stream trouvée")

    proto = info.get("protocol", "https")
    ext   = "m3u8" if "m3u8" in proto else info.get("ext", "mp4")

    return {
        "url":       url,
        "audio_url": None,
        "ext":       ext,
        "protocol":  proto,
        "headers":   _pick_headers(info),
        "title":     title,
        "duration":  duration,
        "merged":    False,
    }


async def resolve_stream_url(embed_url: str) -> dict:
    """Résout une URL embed en URL de stream directe (async wrapper, thread pool)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _resolve_sync, embed_url)


async def build_zip(
    items:            list[dict],
    zip_path:         Path,
    on_progress:      Optional[Callable] = None,       # async (done, total) → None
    cancel:           Optional[threading.Event] = None,
    on_file_progress: Optional[Callable] = None,       # sync (dl, tot, spd, eta) → None
) -> int:
    """
    Télécharge chaque item puis crée un ZIP.
    Retourne le nombre de fichiers intégrés avec succès.
    `on_file_progress` : progression byte-level pour l'item en cours de téléchargement.
    """
    import tempfile

    items = items[:_MAX_ITEMS_PER_ZIP]
    total = len(items)
    tmp   = tempfile.mkdtemp(prefix="anime_zip_")

    try:
        tmp_path    = Path(tmp)
        downloaded: list[tuple[str, Path]] = []

        for i, item in enumerate(items):
            if cancel and cancel.is_set():
                logger.info("build_zip : annulation demandée, arrêt.")
                break
            path = await download_to_file(
                item.get("player_urls") or item["player_url"], tmp_path, item["filename"],
                cancel=cancel, on_progress=on_file_progress,
            )
            if path and path.exists():
                downloaded.append((path.name, path))
            else:
                logger.warning(f"ZIP [{i+1}/{total}] échec : {item['filename']}")

            if on_progress:
                await on_progress(i + 1, total)

        if not downloaded:
            return 0

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for name, path in sorted(downloaded):
                zf.write(path, name)

        return len(downloaded)

    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
