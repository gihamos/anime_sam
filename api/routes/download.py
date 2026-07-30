"""
Routes de téléchargement de vidéos.

Authentification : Bearer token OU ?token=... (query param pour liens directs).

Tous les téléchargements passent par un système de jobs asynchrones :
yt-dlp télécharge le fichier réel sur disque (gère HLS, cookies, merges),
puis le fichier est servi via FileResponse.

  POST /api/download/jobs              → crée un job
  GET  /api/download/jobs/{id}         → statut
  GET  /api/download/jobs/{id}/file    → télécharge le fichier quand prêt
  DELETE /api/download/jobs/{id}       → annule / supprime

Corps POST /api/download/jobs :
  Épisode(s) :  {"slug":"...", "saison_idx":0, "nums":[1,2]}  (nums vide = toute la saison)
  Film :        {"slug":"...", "film_idx":0}

Sortie :
  1 fichier  → .mp4
  N fichiers → .zip

Admin :
  GET  /admin/api/downloads             → historique
  GET  /admin/api/dl-quotas             → quotas configurés
  PUT  /admin/api/dl-quotas/{username}  → créer/modifier
  DELETE /admin/api/dl-quotas/{username}→ supprimer
"""

import asyncio
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer

import db.downloads_repository as dl_repo
import db.repository as repo
from api.dependencies import _validate_token, _enrich_user, require_admin
from services import downloader
from utils.logger import logger
from models.responses import JobCreated, JobStatus, DownloadRecord, DlQuota, OkResponse

router       = APIRouter(prefix="/api/download", tags=["Téléchargement"])
admin_router = APIRouter(prefix="/admin",        tags=["Téléchargement (admin)"])

# ── Auth : header Bearer OU ?token= ──────────────────────────────────────────

_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _get_dl_user(
    bearer: Optional[str] = Depends(_oauth2),
    token:  Optional[str] = Query(None, alias="token"),
) -> dict:
    t = token or bearer
    if not t:
        raise HTTPException(401, "Token d'authentification requis")
    user = await _validate_token(t)
    return await _enrich_user(user)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_video(videos: list[dict]) -> Optional[dict]:
    return next((v for v in videos if v.get("player_url")), None)


def _video_urls(videos: list[dict]) -> list[str]:
    """Toutes les URLs de lecteurs disponibles, dans l'ordre — pour fallback en cascade."""
    return [v["player_url"] for v in videos if v.get("player_url")]


def _safe(s: str) -> str:
    import re
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(s)).strip() or "fichier"


# ══ Système de jobs ═══════════════════════════════════════════════════════════

@dataclass
class _Job:
    id:          str
    username:    str
    slug:        str
    output_name: str           # nom du fichier final (.mp4 ou .zip)
    is_single:   bool          # True → fichier unique mp4 ; False → ZIP
    items:       list[dict]    # [{filename, player_urls}, ...]
    status:      str  = "pending"   # pending | downloading | ready | error
    progress:    int  = 0           # 0-100
    current:     str  = ""
    error:       str  = ""
    dl_bytes:    int   = 0          # octets téléchargés (suivi temps-réel)
    dl_total:    int   = 0          # taille totale estimée
    dl_speed:    float = 0.0        # vitesse en octets/s
    dl_eta:      int   = 0          # secondes restantes
    output_path: Optional[Path]        = None
    _tmp_dir:    Optional[str]         = None
    _cancel:     threading.Event       = field(default_factory=threading.Event)
    created_at:  float = field(default_factory=time.time)
    expires_at:  float = field(default_factory=lambda: time.time() + 3600)


_jobs: dict[str, _Job] = {}
_JOB_TTL = 3600   # fichiers gardés 1 h après completion

# Limite le nombre de téléchargements yt-dlp/ffmpeg simultanés (CPU/bande passante
# du VPS) — utile depuis qu'un téléchargement de saison crée un job par épisode
# au lieu d'un seul job zippé. Les jobs en excès restent "pending" jusqu'à leur tour.
_download_semaphore = asyncio.Semaphore(3)


def _purge_jobs() -> None:
    """Nettoie les jobs et fichiers expirés."""
    now = time.time()
    for jid, job in list(_jobs.items()):
        if now > job.expires_at:
            job._cancel.set()
            if job._tmp_dir:
                shutil.rmtree(job._tmp_dir, ignore_errors=True)
            _jobs.pop(jid, None)


def _get_job(job_id: str, username: str) -> _Job:
    _purge_jobs()
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable ou expiré")
    if job.username != username:
        raise HTTPException(403, "Ce job ne vous appartient pas")
    return job


async def _run_job(job: _Job) -> None:
    """Tâche de fond : télécharge les vidéos et prépare le fichier final.

    Reste "pending" (sans consommer de slot yt-dlp/ffmpeg) tant que
    `_download_semaphore` est saturé par d'autres jobs en cours.
    """
    async with _download_semaphore:
        try:
            job.status = "downloading"
            job._tmp_dir = tempfile.mkdtemp(prefix="anime_dl_")
            tmp_path = Path(job._tmp_dir)
            total = len(job.items)

            def _byte_progress(dl: int, tot: int, spd: float, eta: int) -> None:
                job.dl_bytes = dl
                job.dl_total = tot
                job.dl_speed = spd
                job.dl_eta   = eta
                if tot > 0:
                    job.progress = min(99, int(dl / tot * 100))

            if job.is_single:
                # ── Fichier unique ────────────────────────────────────────────
                item = job.items[0]
                job.current = item["filename"]
                path = await downloader.download_to_file(
                    item["player_urls"], tmp_path, item["filename"],
                    cancel=job._cancel, on_progress=_byte_progress,
                )
                if job._cancel.is_set():
                    job.status = "error"
                    job.error  = "Téléchargement annulé"
                    return
                if not path or not path.exists():
                    job.status = "error"
                    job.error  = (
                        "Impossible de télécharger la vidéo. "
                        "Le lecteur n'est peut-être pas supporté par yt-dlp, "
                        "ou le contenu nécessite une authentification sur le site."
                    )
                    return
                job.output_path = path
                job.progress = 100

                await dl_repo.record(
                    job.username, job.slug, "episode" if "Episode" in job.output_name else "film",
                    nb_files=1, size_bytes=path.stat().st_size, details=job.output_name,
                )

            else:
                # ── Multi-fichiers → ZIP ──────────────────────────────────────
                zip_path = tmp_path / job.output_name

                async def _progress(done: int, total_: int) -> None:
                    job.progress = int(done / total_ * 90)
                    if done > 0:
                        job.current = job.items[done - 1]["filename"]

                nb = await downloader.build_zip(
                    job.items, zip_path, on_progress=_progress,
                    cancel=job._cancel, on_file_progress=_byte_progress,
                )

                if job._cancel.is_set():
                    job.status = "error"
                    job.error  = "Téléchargement annulé"
                    return
                if nb == 0:
                    job.status = "error"
                    job.error  = "Aucune vidéo n'a pu être téléchargée"
                    return

                job.output_path = zip_path
                job.progress = 100

                await dl_repo.record(
                    job.username, job.slug, "season",
                    nb_files=nb, size_bytes=zip_path.stat().st_size,
                    details=job.output_name,
                )

            job.status     = "ready"
            job.expires_at = time.time() + _JOB_TTL
            logger.info(f"Job {job.id} terminé → {job.output_path.name} ({job.output_path.stat().st_size // 1024} Ko)")

        except Exception as exc:
            job.status = "error"
            job.error  = str(exc)
            logger.exception(f"Job {job.id} erreur")


# ══ Routes jobs ════════════════════════════════════════════════════════════════

@router.post("/jobs", response_model=JobCreated, status_code=202, summary="Créer un job de téléchargement")
async def create_job(
    body:       dict,
    background: BackgroundTasks,
    user:       dict = Depends(_get_dl_user),
):
    """
    Corps JSON — épisode(s) :
      {"slug": "naruto", "saison_idx": 0, "nums": [1, 2]}   # nums vide = toute la saison

    Corps JSON — film :
      {"slug": "titre-film", "film_idx": 0}

    Un job avec 1 seul élément retourne un .mp4 ;
    un job avec N > 1 éléments retourne un .zip.
    """
    slug     = str(body.get("slug", "")).strip()
    username = user.get("username", "?")

    # ── Vérification des permissions de téléchargement ──────────────────────
    eff = user.get("_eff")
    if eff and not eff.is_admin:
        if not eff.can_download:
            raise HTTPException(403, "Le téléchargement a été désactivé pour votre compte")
        if slug in eff.dl_forbidden:
            raise HTTPException(403, f"Téléchargement non autorisé pour le catalogue « {slug} »")

    doc = await repo.find_by_slug(slug)
    if not doc:
        raise HTTPException(404, "Catalogue introuvable")

    nom_cat = _safe(doc.get("nom", slug))
    items: list[dict] = []

    # ── Film ────────────────────────────────────────────────────────────────
    if "film_idx" in body:
        film_idx = int(body["film_idx"])
        films    = doc.get("films", [])
        if film_idx >= len(films):
            raise HTTPException(404, "Film introuvable")
        urls = _video_urls(films[film_idx].get("videos", []))
        if not urls:
            raise HTTPException(404, "Aucun lecteur disponible — synchronisez d'abord")
        nom_film = _safe(films[film_idx].get("nom", f"film-{film_idx}"))
        items    = [{"filename": f"{nom_cat} - {nom_film}", "player_urls": urls}]
        output_name = f"{nom_cat} - {nom_film}.mp4"

    # ── Épisode(s) d'une saison ─────────────────────────────────────────────
    elif "saison_idx" in body:
        saison_idx = int(body["saison_idx"])
        saisons    = doc.get("saisons", [])
        if saison_idx >= len(saisons):
            raise HTTPException(404, "Saison introuvable")
        all_eps = saisons[saison_idx].get("episodes", [])
        if not all_eps:
            raise HTTPException(404, "Saison non synchronisée — lancez d'abord la sync")

        nums = body.get("nums")
        if nums:
            num_set = {int(n) for n in nums if str(n).strip().lstrip("-").isdigit()}
            eps = [e for e in all_eps if e.get("numero") in num_set]
        else:
            eps = all_eps

        if not eps:
            raise HTTPException(404, "Aucun épisode correspondant aux filtres")

        nom_sai = _safe(saisons[saison_idx].get("nom", f"saison-{saison_idx}"))
        for ep in eps:
            urls = _video_urls(ep.get("videos", []))
            if urls:
                items.append({
                    "filename":    f"{nom_cat} - {nom_sai} - Episode {ep['numero']:02d}",
                    "player_urls": urls,
                })

        if not items:
            raise HTTPException(404, "Aucun lecteur disponible — synchronisez d'abord")

        if len(items) == 1:
            ep_num = eps[0]["numero"]
            output_name = f"{nom_cat} - {nom_sai} - Episode {ep_num:02d}.mp4"
        else:
            output_name = f"{nom_cat} - {nom_sai}.zip"

    else:
        raise HTTPException(400, "Paramètre requis : saison_idx ou film_idx")

    # ── Vérification quota individuel ────────────────────────────────────────
    ok, reason = await dl_repo.check(username, nb_files=len(items))
    if not ok:
        raise HTTPException(429, reason)

    # ── Vérification quota groupe ─────────────────────────────────────────────
    if eff and not eff.is_admin and eff.dl_quota.get("enabled"):
        usage = await dl_repo.usage_today(username)
        max_f = int(eff.dl_quota.get("max_files_per_day", 20))
        max_b = float(eff.dl_quota.get("max_gb_per_day", 10.0)) * 1024 ** 3
        if usage["count"] + len(items) > max_f:
            raise HTTPException(429, f"Quota groupe dépassé : {usage['count']}/{max_f} fichiers/24 h")
        if usage["bytes"] > max_b:
            gb_used = usage["bytes"] / 1024 ** 3
            raise HTTPException(429, f"Quota volumétrique groupe dépassé : {gb_used:.1f}/{eff.dl_quota['max_gb_per_day']} Go/24 h")

    is_single = len(items) == 1
    job = _Job(
        id          = str(uuid.uuid4()),
        username    = username,
        slug        = slug,
        output_name = output_name,
        is_single   = is_single,
        items       = items,
    )
    _jobs[job.id] = job
    background.add_task(_run_job, job)

    return {
        "job_id":     job.id,
        "nb_items":   len(items),
        "output_name": output_name,
        "is_single":  is_single,
        "status":     job.status,
    }


@router.get("/jobs/{job_id}", response_model=JobStatus, summary="Statut d'un job")
async def job_status(job_id: str, user: dict = Depends(_get_dl_user)):
    job = _get_job(job_id, user.get("username", "?"))
    return {
        "job_id":      job.id,
        "status":      job.status,
        "progress":    job.progress,
        "current":     job.current,
        "dl_bytes":    job.dl_bytes,
        "dl_total":    job.dl_total,
        "dl_speed":    job.dl_speed,
        "dl_eta":      job.dl_eta,
        "output_name": job.output_name,
        "is_single":   job.is_single,
        "nb_items":    len(job.items),
        "error":       job.error,
        "ready":       job.status == "ready",
    }


@router.get("/jobs/{job_id}/file", summary="Télécharger le fichier d'un job terminé")
async def job_file(
    job_id: str,
    token:  Optional[str] = Query(None),
    bearer: Optional[str] = Depends(_oauth2),
):
    t = token or bearer
    if not t:
        raise HTTPException(401, "Token requis")
    user = await _enrich_user(await _validate_token(t))
    job  = _get_job(job_id, user.get("username", "?"))

    if job.status != "ready":
        raise HTTPException(409, f"Job pas encore prêt (statut : {job.status})")
    if not job.output_path or not job.output_path.exists():
        raise HTTPException(410, "Fichier introuvable ou expiré")

    media = "video/mp4" if job.is_single else "application/zip"
    return FileResponse(
        path       = job.output_path,
        media_type = media,
        filename   = job.output_name,
        headers    = {"Content-Disposition": f'attachment; filename="{job.output_name}"'},
    )


@router.delete("/jobs/{job_id}", status_code=204, summary="Annuler / supprimer un job")
async def delete_job(job_id: str, user: dict = Depends(_get_dl_user)):
    job = _get_job(job_id, user.get("username", "?"))
    job._cancel.set()                                   # interrompt yt-dlp via le progress hook
    if job._tmp_dir:
        shutil.rmtree(job._tmp_dir, ignore_errors=True)
    _jobs.pop(job_id, None)


# ══ Routes admin ══════════════════════════════════════════════════════════════

@admin_router.get("/api/downloads", response_model=list[DownloadRecord], summary="Historique des téléchargements")
async def list_downloads(limit: int = 200, _: dict = Depends(require_admin)):
    return await dl_repo.list_recent(limit)


@admin_router.delete("/api/downloads", status_code=200,
                     summary="Vider tout l'historique des téléchargements")
async def clear_all_downloads(_: dict = Depends(require_admin)):
    count = await dl_repo.delete_all()
    return {"deleted": count}


@admin_router.delete("/api/downloads/user/{username}", status_code=200,
                     summary="Supprimer l'historique d'un utilisateur")
async def clear_downloads_by_user(username: str, _: dict = Depends(require_admin)):
    count = await dl_repo.delete_by_username(username)
    return {"deleted": count, "username": username}


@admin_router.delete("/api/downloads/catalogue/{slug}", status_code=200,
                     summary="Supprimer l'historique d'un catalogue")
async def clear_downloads_by_catalogue(slug: str, _: dict = Depends(require_admin)):
    count = await dl_repo.delete_by_slug(slug)
    return {"deleted": count, "slug": slug}


@admin_router.get("/api/dl-quotas", response_model=list[DlQuota], summary="Liste des quotas configurés")
async def list_quotas(_: dict = Depends(require_admin)):
    return await dl_repo.list_quotas()


@admin_router.put("/api/dl-quotas/{username}", response_model=DlQuota, summary="Configurer le quota d'un utilisateur")
async def set_quota(username: str, body: dict, _: dict = Depends(require_admin)):
    max_files = int(body.get("max_files_per_day", 20))
    max_gb    = float(body.get("max_gb_per_day", 10.0))
    can_dl    = bool(body.get("can_download", True))
    await dl_repo.set_quota(username, max_files, max_gb, can_dl)
    return {"ok": True, "username": username,
            "max_files_per_day": max_files, "max_gb_per_day": max_gb, "can_download": can_dl}


@admin_router.delete("/api/dl-quotas/{username}", status_code=204,
                     summary="Supprimer un quota (retour au défaut)")
async def delete_quota(username: str, _: dict = Depends(require_admin)):
    if not await dl_repo.delete_quota(username):
        raise HTTPException(404, f"Quota '{username}' introuvable")
