"""
Téléchargement de scans (chapitres manga) pour lecture hors-ligne.

Le backend télécharge chaque page image depuis les sources externes (avec les
bons headers) et les stocke temporairement. Le mobile récupère ensuite les
pages une par une via des endpoints authentifiés.

TTL des jobs : 12 heures (le mobile peut prendre le temps de tout télécharger).

  POST   /api/download/scan/jobs              → crée un job
  GET    /api/download/scan/jobs/{id}         → statut
  GET    /api/download/scan/jobs/{id}/manifest→ liste chapitres/pages (quand prêt)
  GET    /api/download/scan/jobs/{id}/page    → image individuelle (?c=num&p=idx)
  DELETE /api/download/scan/jobs/{id}         → annule / supprime

Corps POST /api/download/scan/jobs :
  {"slug": "one-piece", "scan_slug": "vf", "chapitre_nums": [1, 2, 3]}
  (chapitre_nums vide = tous les chapitres du scan)

Admin :
  GET  /admin/api/scan-downloads             → historique scan téléchargements
"""

import asyncio
import mimetypes
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer

import db.downloads_repository as dl_repo
import db.repository as repo
from api.dependencies import _validate_token, _enrich_user, require_admin
from utils.logger import logger

router       = APIRouter(prefix="/api/download/scan", tags=["Téléchargement Scans"])
admin_router = APIRouter(prefix="/admin",             tags=["Téléchargement Scans (admin)"])

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


# ──────────────────────────────────────────────────────────────────────────────
# Structures internes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _PageInfo:
    chapitre_num: int
    page_index:   int
    local_path:   Path


@dataclass
class _ChapterInfo:
    num:        int
    titre:      Optional[str]
    page_count: int
    urls:       list[str]
    pages:      list[_PageInfo] = field(default_factory=list)


@dataclass
class _ScanJob:
    id:          str
    username:    str
    slug:        str
    scan_slug:   str
    chapters:    list[_ChapterInfo]
    status:      str   = "pending"
    progress:    int   = 0
    total_pages: int   = 0
    done_pages:  int   = 0
    error:       str   = ""
    created_at:  float = field(default_factory=time.time)
    expires_at:  float = field(default_factory=lambda: time.time() + 43200)  # 12 h
    _cancel:     threading.Event = field(default_factory=threading.Event)
    _tmp_dir:    Optional[str]   = None


_scan_jobs: dict[str, _ScanJob] = {}
_SCAN_JOB_TTL = 43200  # 12 h


def _purge_scan_jobs() -> None:
    now = time.time()
    for jid, job in list(_scan_jobs.items()):
        if now > job.expires_at:
            job._cancel.set()
            if job._tmp_dir:
                shutil.rmtree(job._tmp_dir, ignore_errors=True)
            _scan_jobs.pop(jid, None)


def _get_scan_job(job_id: str, username: str) -> _ScanJob:
    _purge_scan_jobs()
    job = _scan_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable ou expiré")
    if job.username != username:
        raise HTTPException(403, "Ce job ne vous appartient pas")
    return job


# ──────────────────────────────────────────────────────────────────────────────
# Téléchargement pages
# ──────────────────────────────────────────────────────────────────────────────

_PAGE_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


async def _download_page(
    client:  httpx.AsyncClient,
    url:     str,
    dest:    Path,
    referer: str = "",
    retries: int = 3,
) -> bool:
    headers = dict(_PAGE_HEADERS)
    if referer:
        headers["Referer"] = referer
    for attempt in range(retries):
        try:
            r = await client.get(url, headers=headers, follow_redirects=True, timeout=30)
            if r.status_code != 200:
                if attempt < retries - 1:
                    await asyncio.sleep(1.5)
                    continue
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(1.5)
    return False


async def _run_scan_job(job: _ScanJob) -> None:
    try:
        job.status    = "downloading"
        job._tmp_dir  = tempfile.mkdtemp(prefix="anime_scan_")
        tmp_path = Path(job._tmp_dir)
        job.total_pages = sum(len(ch.urls) for ch in job.chapters)

        # Referer : on utilise le domaine anime-sama comme base
        referer = "https://anime-sama.fr/"

        async with httpx.AsyncClient(verify=False) as client:
            for ch in job.chapters:
                if job._cancel.is_set():
                    break
                ch_dir = tmp_path / f"ch_{ch.num:04d}"
                ch_dir.mkdir(exist_ok=True)

                # Téléchargement en parallèle (5 simultanés max par chapitre)
                sem = asyncio.Semaphore(5)

                async def dl_page(p_idx: int, url: str) -> None:
                    async with sem:
                        if job._cancel.is_set():
                            return
                        ext  = url.split("?")[0].rsplit(".", 1)[-1][:5] or "jpg"
                        dest = ch_dir / f"page_{p_idx:04d}.{ext}"
                        ok   = await _download_page(client, url, dest, referer)
                        if ok:
                            ch.pages.append(_PageInfo(ch.num, p_idx, dest))
                        job.done_pages += 1
                        if job.total_pages > 0:
                            job.progress = min(99, int(job.done_pages / job.total_pages * 100))

                await asyncio.gather(*[dl_page(i, u) for i, u in enumerate(ch.urls)])
                # Trier les pages par index (gather ne garantit pas l'ordre dans ch.pages)
                ch.pages.sort(key=lambda p: p.page_index)

        if job._cancel.is_set():
            job.status = "error"
            job.error  = "Téléchargement annulé"
            return

        total_dl = sum(len(ch.pages) for ch in job.chapters)
        if total_dl == 0:
            job.status = "error"
            job.error  = "Aucune page n'a pu être téléchargée (URLs invalides ou protégées)"
            return

        size_bytes = sum(
            p.local_path.stat().st_size
            for ch in job.chapters
            for p in ch.pages
            if p.local_path.exists()
        )
        job.progress   = 100
        job.status     = "ready"
        job.expires_at = time.time() + _SCAN_JOB_TTL
        logger.info(f"ScanJob {job.id} prêt → {total_dl} pages / {size_bytes // 1024} Ko")

        await dl_repo.record(
            job.username, job.slug, "scan",
            nb_files   = total_dl,
            size_bytes = size_bytes,
            details    = f"Scan {job.scan_slug} · {len(job.chapters)} chapitre(s)",
        )

    except Exception as exc:
        job.status = "error"
        job.error  = str(exc)
        logger.exception(f"ScanJob {job.id} erreur")


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=202, summary="Créer un job de téléchargement de scan")
async def create_scan_job(
    body:       dict,
    background: BackgroundTasks,
    user:       dict = Depends(_get_dl_user),
):
    """
    Télécharge les pages de un ou plusieurs chapitres côté serveur (avec les bons
    headers/referers) pour contourner la protection anti-bot des sites sources.

    Interrogez `/status` pour l'avancement, puis `/manifest` pour obtenir la liste
    des pages à télécharger sur l'appareil.
    """
    slug      = str(body.get("slug", "")).strip()
    scan_slug = str(body.get("scan_slug", "")).strip()
    nums_raw  = body.get("chapitre_nums") or []
    username  = user.get("username", "?")
    eff       = user.get("_eff")

    if not slug or not scan_slug:
        raise HTTPException(400, "slug et scan_slug sont requis")

    # ── Permissions ──────────────────────────────────────────────────────────
    if eff and not eff.is_admin:
        if not eff.can_download:
            raise HTTPException(403, "Le téléchargement a été désactivé pour votre compte")
        if slug in eff.dl_forbidden:
            raise HTTPException(403, f"Téléchargement non autorisé pour le catalogue « {slug} »")

    # ── Catalogue ────────────────────────────────────────────────────────────
    doc = await repo.find_by_slug(slug)
    if not doc:
        raise HTTPException(404, "Catalogue introuvable")

    scans = doc.get("scans", [])
    scan  = next((s for s in scans if s.get("slug") == scan_slug), None)
    if not scan:
        raise HTTPException(404, f"Scan « {scan_slug} » introuvable dans ce catalogue")

    chapitres = scan.get("chapitres", [])
    if not chapitres:
        raise HTTPException(404, "Aucun chapitre disponible — synchronisez d'abord le catalogue")

    if nums_raw:
        num_set   = {int(n) for n in nums_raw if str(n).strip().isdigit()}
        chapitres = [c for c in chapitres if c.get("numero") in num_set]
    if not chapitres:
        raise HTTPException(404, "Aucun chapitre correspondant aux numéros demandés")

    chapters_info: list[_ChapterInfo] = []
    for ch in chapitres:
        images = ch.get("images", [])
        if not images:
            continue
        chapters_info.append(_ChapterInfo(
            num        = int(ch["numero"]),
            titre      = ch.get("titre"),
            page_count = len(images),
            urls       = list(images),
        ))

    if not chapters_info:
        raise HTTPException(
            404,
            "Aucune image disponible dans les chapitres sélectionnés — "
            "lancez d'abord une synchronisation du catalogue"
        )

    total_pages = sum(c.page_count for c in chapters_info)

    # ── Quota ─────────────────────────────────────────────────────────────────
    ok, reason = await dl_repo.check(username, nb_files=total_pages)
    if not ok:
        raise HTTPException(429, reason)

    if eff and not eff.is_admin and eff.dl_quota.get("enabled"):
        usage = await dl_repo.usage_today(username)
        max_f = int(eff.dl_quota.get("max_files_per_day", 20))
        if usage["count"] + total_pages > max_f:
            raise HTTPException(429, f"Quota groupe dépassé : {usage['count']}/{max_f} pages/24 h")

    # ── Création job ──────────────────────────────────────────────────────────
    job = _ScanJob(
        id        = str(uuid.uuid4()),
        username  = username,
        slug      = slug,
        scan_slug = scan_slug,
        chapters  = chapters_info,
    )
    _scan_jobs[job.id] = job
    background.add_task(_run_scan_job, job)

    return {
        "job_id":      job.id,
        "slug":        slug,
        "scan_slug":   scan_slug,
        "chapters":    [{"num": c.num, "titre": c.titre, "page_count": c.page_count}
                        for c in chapters_info],
        "total_pages": total_pages,
        "status":      job.status,
    }


@router.get("/jobs/{job_id}", summary="Statut d'un job scan")
async def scan_job_status(job_id: str, user: dict = Depends(_get_dl_user)):
    job = _get_scan_job(job_id, user.get("username", "?"))
    return {
        "job_id":      job.id,
        "status":      job.status,
        "progress":    job.progress,
        "total_pages": job.total_pages,
        "done_pages":  job.done_pages,
        "error":       job.error,
        "ready":       job.status == "ready",
    }


@router.get("/jobs/{job_id}/manifest", summary="Manifest du job (chapitres et pages, quand prêt)")
async def scan_job_manifest(job_id: str, user: dict = Depends(_get_dl_user)):
    """
    Retourne la liste des chapitres et leur nombre de pages disponibles.
    Utilisez ensuite `/page?c={num}&p={idx}` pour télécharger chaque image.
    """
    job = _get_scan_job(job_id, user.get("username", "?"))
    if job.status != "ready":
        raise HTTPException(409, f"Job pas encore prêt (statut : {job.status})")
    return {
        "job_id":    job.id,
        "slug":      job.slug,
        "scan_slug": job.scan_slug,
        "chapters":  [
            {
                "num":        ch.num,
                "titre":      ch.titre,
                "page_count": len(ch.pages),
            }
            for ch in job.chapters
        ],
    }


@router.get("/jobs/{job_id}/page", summary="Télécharger une page image (c=num, p=index)")
async def scan_job_page(
    job_id: str,
    c:      int = Query(..., description="Numéro du chapitre"),
    p:      int = Query(..., description="Index de page (0-based)"),
    token:  Optional[str] = Query(None),
    bearer: Optional[str] = Depends(_oauth2),
):
    """
    Sert l'image de la page `p` du chapitre `c`. Auth via Bearer header ou ?token=…
    """
    t = token or bearer
    if not t:
        raise HTTPException(401, "Token requis")
    user = await _enrich_user(await _validate_token(t))
    job  = _get_scan_job(job_id, user.get("username", "?"))

    if job.status != "ready":
        raise HTTPException(409, "Job pas encore prêt")

    ch_info = next((ch for ch in job.chapters if ch.num == c), None)
    if not ch_info:
        raise HTTPException(404, f"Chapitre {c} absent de ce job")

    if p < 0 or p >= len(ch_info.pages):
        raise HTTPException(
            404,
            f"Page {p} hors limites — chapitre {c} a {len(ch_info.pages)} pages téléchargées"
        )

    page = ch_info.pages[p]
    if not page.local_path.exists():
        raise HTTPException(410, "Fichier expiré ou introuvable")

    mime = mimetypes.guess_type(str(page.local_path))[0] or "image/jpeg"
    return FileResponse(page.local_path, media_type=mime)


@router.delete("/jobs/{job_id}", status_code=204, summary="Annuler / supprimer un job scan")
async def delete_scan_job(job_id: str, user: dict = Depends(_get_dl_user)):
    job = _get_scan_job(job_id, user.get("username", "?"))
    job._cancel.set()
    if job._tmp_dir:
        shutil.rmtree(job._tmp_dir, ignore_errors=True)
    _scan_jobs.pop(job_id, None)


# ──────────────────────────────────────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────────────────────────────────────

@admin_router.get(
    "/api/scan-downloads",
    summary="Historique des téléchargements de scans (admin)",
    tags=["Téléchargement Scans (admin)"],
)
async def list_scan_downloads(
    limit: int  = 200,
    _:     dict = Depends(require_admin),
):
    """Retourne l'historique des téléchargements de type 'scan'."""
    return await dl_repo.list_recent_by_type("scan", limit)


@admin_router.get(
    "/api/scan-downloads/user/{username}",
    summary="Historique scan d'un utilisateur (admin)",
    tags=["Téléchargement Scans (admin)"],
)
async def list_scan_downloads_by_user(
    username: str,
    limit:    int  = 100,
    _:        dict = Depends(require_admin),
):
    return await dl_repo.list_recent_by_type_and_user("scan", username, limit)
