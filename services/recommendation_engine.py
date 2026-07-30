"""
Moteur de recommandations personnalisées — "content-based" par similarité de vecteurs.

Chaque catalogue est représenté par un vecteur pondéré construit à partir de ses
métadonnées AniList (`enrichment`, voir services/enrichment_service.py) :
  - un terme "genre:X"  poids 1.0 par genre
  - un terme "tag:X"    poids rank/100 (AniList tags, uniquement rank >= 40 pour limiter le bruit)
  - un terme "studio:X" poids 0.6 par studio/staff principal
Si `enrichment` est vide (catalogue pas encore enrichi), on retombe sur les genres bruts
(`catalogue.genres`) seuls — le moteur reste utilisable pour 100% des catalogues, enrichis
ou non.

Deux usages :
  - compute_recommendations : profil utilisateur = somme des vecteurs des favoris,
    score = similarité cosinus + bonus qualité (score AniList / note) + bonus état.
    Inclut un `reason` (« Parce que vous aimez X ») pointant vers le favori le plus proche.
  - get_similar_catalogues  : similarité item-item indépendante des favoris (« Titres
    similaires » en page détail), reason = plus fort terme partagé (tag/genre/studio).

Ce module est indépendant des routes FastAPI : il peut être importé
par n'importe quelle autre partie de l'application (planificateur,
webhooks, d'autres plateformes appelant le backend directement…).
"""

from __future__ import annotations

import math
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
# Vecteurs de caractéristiques et similarité
# ---------------------------------------------------------------------------

_MIN_TAG_RANK  = 40     # ignore les tags AniList peu pertinents (bruit)
_TAG_SCALE     = 100.0  # AniList exprime `rank` sur 0-100
_STUDIO_WEIGHT = 0.6


def _feature_vector(cat: dict) -> dict[str, float]:
    """
    Vecteur pondéré {terme: poids} décrivant un catalogue — base de toute similarité
    cosinus dans ce module. Repli sur `genres` bruts si `enrichment` est vide/absent
    (catalogue pas encore enrichi par le pipeline AniList) : le moteur reste utilisable
    pour 100% des catalogues.
    """
    enrichment = cat.get("enrichment") or {}
    vec: Counter[str] = Counter()

    for g in (enrichment.get("genres") or cat.get("genres") or []):
        vec[f"genre:{g}"] += 1.0

    for tag in (enrichment.get("tags") or []):
        rank = tag.get("rank") or 0
        name = tag.get("name")
        if name and rank >= _MIN_TAG_RANK:
            vec[f"tag:{name}"] += rank / _TAG_SCALE

    for studio in (enrichment.get("studios_ou_staff") or []):
        vec[f"studio:{studio}"] += _STUDIO_WEIGHT

    return dict(vec)


def _cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Similarité cosinus pure Python entre deux vecteurs creux (pas de numpy)."""
    common = v1.keys() & v2.keys()
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    if dot == 0:
        return 0.0
    norm1 = math.sqrt(sum(w * w for w in v1.values()))
    norm2 = math.sqrt(sum(w * w for w in v2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _sum_vectors(vectors: list[dict[str, float]]) -> dict[str, float]:
    total: Counter[str] = Counter()
    for v in vectors:
        total.update(v)
    return dict(total)


def _top_shared_term(v1: dict[str, float], v2: dict[str, float]) -> Optional[str]:
    """Terme commun (genre/tag/studio) au poids combiné le plus élevé entre deux vecteurs."""
    common = v1.keys() & v2.keys()
    if not common:
        return None
    return max(common, key=lambda k: v1[k] * v2[k])


def _term_label(term: str) -> str:
    _, _, name = term.partition(":")
    return name or term


def _quality_bonus(cat: dict) -> float:
    """Petit bonus qualité (jusqu'à +0.15) — score AniList /100 en priorité, sinon note /10."""
    enrichment = cat.get("enrichment") or {}
    score = enrichment.get("score")
    if score is not None:
        return (score / 100) * 0.15
    return ((cat.get("note") or 0) / 10) * 0.15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_item(cat: dict, score: float = 0.0, reason: Optional[str] = None) -> dict:
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
        "enrichment": cat.get("enrichment") or {},
        "reason":     reason,
    }


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
            "enrichment": doc.get("enrichment") or {},
        })

    return slugs, catalogues


async def compute_recommendations(
    user: dict,
    limit: int = 20,
) -> list[dict]:
    """
    Calcule les recommandations personnalisées pour un utilisateur.

    Profil utilisateur = somme des vecteurs de caractéristiques (genres/tags/studios) de
    ses favoris. Score = similarité cosinus avec ce profil + bonus qualité (score AniList
    ou note) + bonus type dominant + bonus état "en cours". Chaque résultat porte un
    `reason` pointant vers le favori le plus proche (« Parce que vous aimez X »).

    Paramètres
    ----------
    user  : dict enrichi avec _eff (issu de get_current_user)
    limit : nombre maximum de résultats (1-50)
    """
    username = user.get("username", "")
    slugs    = await user_repo.get_favoris(username)

    # Récupérer tous les candidats (avec le champ visibility)
    all_candidates = await catalogue_repo.get_reco_candidates()

    # Filtrer par droits d'accès : l'utilisateur ne voit que ce qu'il a le droit de voir
    candidates = [c for c in all_candidates if user_can_access_catalogue(c, user)]

    # ── Cold start : aucun favori ── récents, popularité AniList en tri secondaire ──
    if not slugs:
        recent = sorted(
            candidates,
            key=lambda x: (x.get("updated_at") or "", (x.get("enrichment") or {}).get("popularity") or 0),
            reverse=True,
        )
        return [_format_item(c, 0.0) for c in recent[:limit]]

    fav_set  = set(slugs)
    fav_cats = [c for c in candidates if c.get("slug") in fav_set]

    # ── Profil utilisateur : vecteurs de caractéristiques des favoris ─────────────
    fav_vectors = {c["slug"]: _feature_vector(c) for c in fav_cats}
    fav_vectors = {s: v for s, v in fav_vectors.items() if v}  # ignore les vecteurs vides

    if not fav_vectors:
        # Aucun favori exploitable (pas de genres/enrichment) → repli sur les récents
        recent = sorted(
            [c for c in candidates if c.get("slug") not in fav_set],
            key=lambda x: x.get("updated_at") or "",
            reverse=True,
        )
        return [_format_item(c, 0.0) for c in recent[:limit]]

    profile_vector = _sum_vectors(list(fav_vectors.values()))
    type_counts    = Counter(c.get("type_contenu") for c in fav_cats if c.get("type_contenu"))
    dominant_type  = type_counts.most_common(1)[0][0] if type_counts else None

    # ── Scoring ───────────────────────────────────────────────────────────────
    scored: list[dict] = []

    for cat in candidates:
        if cat.get("slug") in fav_set:
            continue  # exclure les favoris existants

        cat_vector = _feature_vector(cat)
        similarity = _cosine(profile_vector, cat_vector)
        if similarity == 0:
            continue  # aucune caractéristique commune avec le profil → non pertinent

        type_bonus  = 0.15 if (dominant_type and cat.get("type_contenu") == dominant_type) else 0.0
        state_bonus = 0.10 if cat.get("etat") == "en_cours" else 0.0
        quality     = _quality_bonus(cat)

        final_score = similarity + type_bonus + state_bonus + quality

        # Reason : le favori dont le vecteur individuel est le plus proche de ce candidat
        best_slug, best_sim = None, 0.0
        for fav_slug, fav_vec in fav_vectors.items():
            sim = _cosine(fav_vec, cat_vector)
            if sim > best_sim:
                best_slug, best_sim = fav_slug, sim
        reason = None
        if best_slug:
            fav_nom = next((c.get("nom") for c in fav_cats if c.get("slug") == best_slug), best_slug)
            reason = f"Parce que vous aimez {fav_nom}"

        scored.append(_format_item(cat, final_score, reason))

    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]


async def get_similar_catalogues(
    slug: str,
    user: Optional[dict],
    limit: int = 10,
) -> list[dict]:
    """
    Titres similaires à `slug`, indépendamment des favoris d'un utilisateur — alimente la
    section "Titres similaires" de la page détail. Similarité cosinus sur les vecteurs de
    caractéristiques (genres/tags/studios), `reason` = terme partagé le plus significatif.
    """
    all_candidates = await catalogue_repo.get_reco_candidates()
    target = next((c for c in all_candidates if c.get("slug") == slug), None)
    if not target:
        return []

    if user is not None:
        candidates = [c for c in all_candidates if user_can_access_catalogue(c, user)]
    else:
        candidates = [c for c in all_candidates if (c.get("visibility") or {}).get("is_public", False)]

    target_vector = _feature_vector(target)
    if not target_vector:
        return []

    scored: list[dict] = []
    for cat in candidates:
        if cat.get("slug") == slug:
            continue
        cat_vector = _feature_vector(cat)
        similarity = _cosine(target_vector, cat_vector)
        if similarity == 0:
            continue
        shared = _top_shared_term(target_vector, cat_vector)
        reason = f"Similaire pour « {_term_label(shared)} »" if shared else None
        scored.append(_format_item(cat, similarity, reason))

    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]
