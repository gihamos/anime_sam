"""
Moteur de recommandations personnalisées.

Algorithme multi-critères basé sur les favoris d'un utilisateur :
  - Genre weighting  : les genres les plus fréquents dans les favoris pèsent plus
  - Type preference  : bonus si le type dominant (anime/film/scan) correspond
  - State bonus      : légère préférence pour les séries en cours
  - Note bonus       : intègre la note si disponible
  - Cold start       : si aucun favori → retourne du contenu récent accessible

Ce module est indépendant des routes FastAPI : il peut être importé
par n'importe quelle autre partie de l'application (planificateur,
webhooks, d'autres plateformes appelant le backend directement…).
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

import db.repository as catalogue_repo
import db.user_repository as user_repo


# ---------------------------------------------------------------------------
# Contrôle d'accès
# ---------------------------------------------------------------------------

def user_can_access_catalogue(cat: dict, user: dict) -> bool:
    """
    Retourne True si l'utilisateur a le droit de voir ce catalogue.
    Réplique la logique de filter_catalogue_for_user sans lever d'exception.
    """
    from api.dependencies import EffectiveAccess  # import local pour éviter le cycle

    slug      = cat.get("slug", "")
    vis       = cat.get("visibility", {})
    is_public = vis.get("is_public", False)

    # Admin → accès total
    if user.get("role") == "admin":
        return True

    eff = user.get("_eff")
    if not (eff and isinstance(eff, EffectiveAccess)):
        return is_public

    allowed_slugs = eff.allowed_slugs or set()
    genre_access  = eff.genre_access  or set()

    # Aucune restriction de groupe → seulement les catalogues publics
    if not (allowed_slugs or genre_access):
        return is_public

    cat_genres = {g.lower() for g in cat.get("genres", [])}
    if (slug in allowed_slugs) or bool(cat_genres & genre_access):
        return True  # accès explicite via groupe ou genre

    return is_public  # pas d'accès explicite → retomber sur la visibilité publique


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_item(cat: dict, score: float = 0.0) -> dict:
    """Formate un catalogue candidat en item de recommandation."""
    return {
        "slug":   cat.get("slug"),
        "nom":    cat.get("nom"),
        "image":  cat.get("image"),
        "genres": cat.get("genres") or [],
        "type":   cat.get("type_contenu"),   # normalisé à "type" pour l'API publique
        "langue": cat.get("langue"),
        "etat":   cat.get("etat"),
        "annee":  cat.get("annee"),
        "note":   cat.get("note"),
        "score":  round(score, 4),
    }


async def _build_user_profile(slugs: list[str]) -> tuple[Counter, Counter]:
    """
    Construit le profil de préférences de l'utilisateur depuis ses favoris.
    Retourne (genre_freq, type_freq).
    """
    genre_freq: Counter[str] = Counter()
    type_freq:  Counter[str] = Counter()

    for slug in slugs:
        doc = await catalogue_repo.find_by_slug(slug)
        if not doc:
            continue
        for g in doc.get("genres") or []:
            genre_freq[g] += 1
        t = doc.get("type_contenu")
        if t:
            type_freq[t] += 1

    return genre_freq, type_freq


# ---------------------------------------------------------------------------
# API publique du moteur
# ---------------------------------------------------------------------------

async def get_favourites_for_user(username: str) -> tuple[list[str], list[dict]]:
    """
    Retourne (slugs, catalogues_details) pour un utilisateur.
    Les détails incluent les champs nécessaires à l'affichage (image, genres…).
    """
    slugs = await user_repo.get_favoris(username)
    catalogues: list[dict] = []

    for slug in slugs:
        doc = await catalogue_repo.find_by_slug(slug)
        if not doc:
            continue
        catalogues.append({
            "slug":   doc.get("slug"),
            "nom":    doc.get("nom"),
            "image":  doc.get("image"),
            "genres": doc.get("genres") or [],
            "type":   doc.get("type_contenu"),
            "etat":   doc.get("etat"),
            "langues": doc.get("langues") or [],
            "annee":  doc.get("annee"),
            "note":   doc.get("note"),
        })

    return slugs, catalogues


async def compute_recommendations(
    user: dict,
    limit: int = 20,
) -> list[dict]:
    """
    Calcule les recommandations personnalisées pour un utilisateur.

    Paramètres
    ----------
    user  : dict enrichi avec _eff (issu de get_current_user)
    limit : nombre maximum de résultats (1-50)

    Retourne
    --------
    Liste d'items triés par score décroissant, chacun avec les champs :
    slug, nom, image, genres, type, langue, etat, annee, note, score
    """
    username = user.get("username", "")
    slugs    = await user_repo.get_favoris(username)

    # Récupérer tous les candidats (avec le champ visibility)
    all_candidates = await catalogue_repo.get_reco_candidates()

    # Filtrer par droits d'accès : l'utilisateur ne voit que ce qu'il a le droit de voir
    candidates = [c for c in all_candidates if user_can_access_catalogue(c, user)]

    # ── Cold start : aucun favori ─────────────────────────────────────────────
    if not slugs:
        recent = sorted(candidates, key=lambda x: x.get("updated_at") or "", reverse=True)
        return [_format_item(c, 0.0) for c in recent[:limit]]

    fav_set = set(slugs)

    # ── Profil utilisateur ────────────────────────────────────────────────────
    genre_freq, type_freq = await _build_user_profile(slugs)

    # Si les favoris n'ont aucun genre renseigné → retourne les récents
    if not genre_freq:
        recent = sorted(
            [c for c in candidates if c.get("slug") not in fav_set],
            key=lambda x: x.get("updated_at") or "",
            reverse=True,
        )
        return [_format_item(c, 0.0) for c in recent[:limit]]

    total         = len(slugs)
    dominant_type = type_freq.most_common(1)[0][0] if type_freq else None

    # ── Scoring ───────────────────────────────────────────────────────────────
    scored: list[dict] = []

    for cat in candidates:
        if cat.get("slug") in fav_set:
            continue  # exclure les favoris existants

        cat_genres = set(cat.get("genres") or [])

        # Score principal : fréquence relative des genres communs avec les favoris
        genre_score = sum(genre_freq[g] / total for g in cat_genres if g in genre_freq)
        if genre_score == 0:
            continue  # aucun genre commun → non pertinent

        # Bonus type : +0.30 si le type dominant des favoris correspond
        type_bonus = 0.30 if (dominant_type and cat.get("type_contenu") == dominant_type) else 0.0

        # Bonus état : +0.10 pour les séries en cours (contenu vivant)
        state_bonus = 0.10 if cat.get("etat") == "en_cours" else 0.0

        # Bonus note : jusqu'à +0.20 selon la note /10
        note_bonus = ((cat.get("note") or 0) / 10) * 0.20

        final_score = genre_score + type_bonus + state_bonus + note_bonus
        scored.append(_format_item(cat, final_score))

    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]
