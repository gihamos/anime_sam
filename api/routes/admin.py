"""
API d'administration (montée sur le serveur principal — port API).

GET  /admin/api/catalogues                    → liste avec visibilité (admin)
PUT  /admin/api/catalogues/{slug}/visibility  → met à jour la visibilité (admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from models.catalogue import CatalogueVisibility
import db.repository as repo
from api.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/api/catalogues", summary="Catalogues avec visibilité (admin)")
async def list_catalogues_admin(_: dict = Depends(require_admin)):
    items = await repo.get_all_summary()
    result = []
    for item in items:
        doc = await repo.find_by_slug(item["slug"])
        if doc:
            result.append({
                "slug":        doc.get("slug"),
                "nom":         doc.get("nom"),
                "type_contenu":doc.get("type_contenu", "anime"),
                "genres":      doc.get("genres", []),
                "saisons":     [{"slug": s.get("slug"), "nom": s.get("nom"), "lang": s.get("lang")}
                                for s in doc.get("saisons", [])],
                "films":       [{"slug": f.get("slug"), "nom": f.get("nom"), "lang": f.get("lang")}
                                for f in doc.get("films", [])],
                "scans":       [{"slug": s.get("slug"), "nom": s.get("nom")}
                                for s in doc.get("scans", [])],
                "visibility":  doc.get("visibility", {
                    "is_public": True,
                    "public_saisons": [],
                    "public_films": [],
                    "public_scans": [],
                }),
            })
    return result


@router.put(
    "/api/catalogues/{slug}/visibility",
    summary="Mettre à jour la visibilité (admin)",
)
async def update_visibility(
    slug: str,
    body: CatalogueVisibility,
    _:    dict = Depends(require_admin),
):
    found = await repo.update_catalogue_visibility(slug, body.model_dump())
    if not found:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")
    return {"ok": True, "slug": slug, "visibility": body.model_dump()}
