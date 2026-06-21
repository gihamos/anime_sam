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
    player_url:  str,
    dest:        Path,
    stem:        str,
    cancel:      Optional[threading.Event] = None,
    on_progress: Optional[Callable]        = None,
) -> Optional[Path]:
    """Télécharge une vidéo sur disque via yt-dlp (async wrapper)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _download_to_dir_sync, player_url, dest, stem, cancel, on_progress
    )


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
                item["player_url"], tmp_path, item["filename"],
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
