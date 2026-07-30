"""
Modèles de réponse pour la documentation OpenAPI (ReDoc).

Chaque modèle porte :
  - des descriptions sur les champs (Field description)
  - un exemple concret (model_config / json_schema_extra)

Ces modèles sont utilisés via response_model= sur chaque route
afin que ReDoc affiche la structure ET un exemple de sortie.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  FAVORIS & RECOMMANDATIONS
# ══════════════════════════════════════════════════════════════════════════════

class FavorisItem(BaseModel):
    """Résumé d'un catalogue favori."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slug": "naruto", "nom": "Naruto",
        "image": "https://cdn.anime-sama.fr/s2/illus/naruto.jpg",
        "genres": ["Action", "Aventure"], "type": "anime",
        "etat": "termine", "langues": ["vostfr", "vf"],
        "annee": 2002, "note": 8.5,
    }})
    slug:    str           = Field(description="Identifiant unique")
    nom:     str           = Field(description="Titre principal")
    image:   Optional[str] = Field(default=None)
    genres:  list[str]     = Field(default_factory=list)
    type:    Optional[str] = Field(default=None, description="anime | scan | film | autre")
    etat:    Optional[str] = Field(default=None, description="en_cours | termine | abandonne")
    langues: list[str]     = Field(default_factory=list)
    annee:   Optional[int] = Field(default=None)
    note:    Optional[float] = Field(default=None, description="Note sur 10")
    enrichment: dict       = Field(
        default_factory=dict,
        description="Métadonnées AniList (score, tags, studios, banner_url…) — vide si non enrichi",
    )


class FavorisResponse(BaseModel):
    """Réponse de GET /auth/me/favoris."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slugs": ["naruto", "one-piece"],
        "catalogues": [
            {"slug": "naruto", "nom": "Naruto", "image": "...", "genres": ["Action"],
             "type": "anime", "etat": "termine", "langues": ["vostfr"], "annee": 2002, "note": 8.5},
        ],
    }})
    slugs:      list[str]        = Field(description="Slugs des catalogues favoris")
    catalogues: list[FavorisItem] = Field(description="Détails des catalogues favoris")


class RecommendationItem(BaseModel):
    """Élément retourné par le moteur de recommandations."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slug": "bleach", "nom": "Bleach",
        "image": "https://cdn.anime-sama.fr/s2/illus/bleach.jpg",
        "genres": ["Action", "Aventure", "Shônen"],
        "type": "anime", "langue": "vostfr", "etat": "termine",
        "annee": 2004, "note": 8.2, "score": 0.8750,
    }})
    slug:   str            = Field(description="Identifiant unique")
    nom:    str            = Field(description="Titre principal")
    image:  Optional[str]  = Field(default=None)
    genres: list[str]      = Field(default_factory=list)
    type:   Optional[str]  = Field(default=None, description="anime | scan | film | autre")
    langue: Optional[str]  = Field(default=None)
    etat:   Optional[str]  = Field(default=None)
    annee:  Optional[int]  = Field(default=None)
    note:   Optional[float] = Field(default=None, description="Note sur 10")
    score:  float           = Field(
        default=0.0,
        description=(
            "Score de pertinence calculé par le moteur de recommandations. "
            "0.0 = cold start (aucun favori). Plus élevé = plus pertinent."
        ),
    )
    enrichment: dict       = Field(
        default_factory=dict,
        description="Métadonnées AniList (score, tags, studios, banner_url…) — vide si non enrichi",
    )
    reason: Optional[str]  = Field(
        default=None,
        description="Explication lisible de la recommandation (ex. « Parce que vous aimez Naruto »)",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

class TokenResponse(BaseModel):
    """Jeton d'accès retourné après une authentification réussie."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1MzA1NjAwMH0.abc123",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInR5cGUiOiJyZWZyZXNoIn0.xyz789",
        "token_type":    "bearer",
    }})

    access_token:  str            = Field(description="JWT Bearer — passer dans Authorization: Bearer <token>")
    refresh_token: Optional[str]  = Field(default=None, description="Refresh token (30 jours) — utiliser sur POST /auth/refresh")
    token_type:    str            = Field(default="bearer", description="Toujours 'bearer'")


# ══════════════════════════════════════════════════════════════════════════════
#  CATALOGUE — résumé (liste)
# ══════════════════════════════════════════════════════════════════════════════

class SaisonSummary(BaseModel):
    slug:           str           = Field(description="Identifiant URL de la saison")
    nom:            str           = Field(description="Nom affiché (ex: 'Saison 1 VOSTFR')")
    lang:           str           = Field(description="Langue : vostfr | vf | vo | vastfr")
    total_episodes: int           = Field(default=0, description="Nombre total d'épisodes")


class FilmSummary(BaseModel):
    slug: str = Field(description="Identifiant URL du film")
    nom:  str = Field(description="Nom affiché")
    lang: str = Field(description="Langue")


class ScanSummary(BaseModel):
    slug: str = Field(description="Identifiant URL du scan")
    nom:  str = Field(description="Nom affiché")


class CatalogueSummary(BaseModel):
    """Résumé d'un catalogue (sans épisodes ni chapitres détaillés)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slug": "naruto",
        "nom": "Naruto",
        "titre_alternatif": "ナルト",
        "synopsis": "Naruto Uzumaki, un jeune ninja qui rêve de devenir Hokage…",
        "image": "https://cdn.anime-sama.fr/s2/illus/naruto.jpg",
        "type_contenu": "anime",
        "etat": "termine",
        "genres": ["Action", "Aventure", "Shônen"],
        "langues": ["vostfr", "vf"],
        "episodes_synced": True,
        "updated_at": "2026-06-15T10:30:00",
        "created_at": "2026-01-01T00:00:00",
        "saisons": [
            {"slug": "saison1", "nom": "Saison 1 VOSTFR", "lang": "vostfr", "total_episodes": 220},
            {"slug": "saison1", "nom": "Saison 1 VF",     "lang": "vf",     "total_episodes": 220},
        ],
        "films": [
            {"slug": "film1", "nom": "Naruto le film : La Princesse des neiges", "lang": "vostfr"},
        ],
        "scans": [],
    }})

    slug:             str               = Field(description="Identifiant unique (extrait de l'URL)")
    nom:              str               = Field(description="Titre principal")
    titre_alternatif: Optional[str]     = Field(default=None, description="Titre alternatif (japonais, anglais…)")
    synopsis:         Optional[str]     = Field(default=None, description="Résumé (tronqué à 200 caractères dans la liste)")
    image:            Optional[str]     = Field(default=None, description="URL de l'illustration")
    type_contenu:     Optional[str]     = Field(default=None, description="anime | scan | film | autre — absent si trouvé uniquement via le scraping du site (in_db=False)")
    etat:             Optional[str]     = Field(default=None, description="en_cours | termine | abandonne — absent si in_db=False")
    genres:           list[str]         = Field(default_factory=list)
    langues:          list[str]         = Field(default_factory=list, description="Langues disponibles")
    episodes_synced:  bool              = Field(default=False, description="True si les épisodes ont été synchronisés")
    annee:            Optional[int]     = Field(default=None, description="Année de sortie")
    note:             Optional[float]   = Field(default=None, description="Note sur 10")
    updated_at:       Optional[str]     = Field(default=None, description="Date ISO de dernière mise à jour")
    created_at:       Optional[str]     = Field(default=None, description="Date ISO de création")
    saisons:          list[SaisonSummary] = Field(default_factory=list)
    films:            list[FilmSummary]   = Field(default_factory=list)
    scans:            list[ScanSummary]   = Field(default_factory=list)
    enrichment:       dict               = Field(
        default_factory=dict,
        description="Métadonnées AniList (score, tags, studios, banner_url…) — vide si non enrichi",
    )
    in_db:            bool               = Field(
        default=True,
        description="False si ce résultat vient uniquement du scraping en direct d'anime-sama.to (pas encore en base) — voir GET /catalogues/rechercher",
    )


class SiteSearchResult(BaseModel):
    """Résultat de recherche scrappé directement depuis le site (structure allégée)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "nom": "Japan Sinks 2020",
        "slug": "japan-sinks-2020",
        "url": "https://anime-sama.to/catalogue/japan-sinks-2020",
        "image": "https://raw.githubusercontent.com/Anime-Sama/IMG/img/contenu/japan-sinks-2020.jpg",
        "genres": ["Action", "Drame", "Science-fiction", "Apocalypse"],
    }})

    nom:    str           = Field(description="Titre")
    slug:   Optional[str] = Field(default=None)
    url:    Optional[str] = Field(default=None)
    image:  Optional[str] = Field(default=None)
    genres: list[str]     = Field(default_factory=list)


class CatalogueAdminSummary(CatalogueSummary):
    """Résumé enrichi pour l'admin (inclut la visibilité)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        **CatalogueSummary.model_config["json_schema_extra"]["example"],  # type: ignore[index]
        "visibility": {
            "is_public": False,
            "public_saisons": [],
            "public_films": [],
            "public_scans": [],
        },
    }})

    visibility: dict = Field(default_factory=dict, description="Contrôle d'accès public")


# ══════════════════════════════════════════════════════════════════════════════
#  SYNC
# ══════════════════════════════════════════════════════════════════════════════

class SyncStarted(BaseModel):
    """Confirmation de démarrage d'une synchronisation."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "started",
        "slug": "naruto",
        "nb_saisons": 3,
        "nb_films": 2,
        "nb_scans": 0,
        "ws": "/catalogues/naruto/sync-content/ws",
    }})

    status:     str           = Field(description="Toujours 'started'")
    slug:       str
    nb_saisons: int           = Field(default=0)
    nb_films:   int           = Field(default=0)
    nb_scans:   int           = Field(default=0)
    ws:         str           = Field(description="URL du WebSocket pour suivre la progression")


class SyncStatusResponse(BaseModel):
    """État courant de la synchronisation d'un catalogue."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slug": "naruto",
        "status": "syncing",
        "progress": 42,
        "message": "Saison 1 VOSTFR — épisode 92/220",
        "started_at": "2026-06-21T14:05:00",
    }})

    slug:       str           = Field(description="Slug du catalogue")
    status:     str           = Field(description="idle | syncing | done | error | never_synced")
    progress:   int           = Field(default=0, description="Progression en pourcentage (0–100)")
    message:    Optional[str] = Field(default=None, description="Détail de l'étape en cours")
    started_at: Optional[str] = Field(default=None, description="Date ISO de début")


class SyncGlobalStatus(BaseModel):
    """État global du gestionnaire de synchronisations."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "active_syncs": ["naruto", "dragon-ball"],
        "max_concurrent": 3,
        "cooldown_hours": 7,
    }})

    active_syncs:   list[str] = Field(description="Slugs des catalogues en cours de sync")
    max_concurrent: int       = Field(description="Nombre max de syncs simultanées")
    cooldown_hours: int       = Field(description="Délai minimum entre deux syncs du même catalogue")


class SlugStatus(BaseModel):
    """Réponse simple statut + slug."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "pausing", "slug": "naruto",
    }})
    status: str
    slug:   str


# ══════════════════════════════════════════════════════════════════════════════
#  TÉLÉCHARGEMENTS (utilisateur)
# ══════════════════════════════════════════════════════════════════════════════

class JobCreated(BaseModel):
    """Confirmation de création d'un job de téléchargement."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "nb_items": 3,
        "output_name": "Naruto - Saison 1 VOSTFR.zip",
        "is_single": False,
        "status": "pending",
    }})

    job_id:      str  = Field(description="Identifiant unique du job")
    nb_items:    int  = Field(description="Nombre d'épisodes / films à télécharger")
    output_name: str  = Field(description="Nom du fichier produit (.mp4 ou .zip)")
    is_single:   bool = Field(description="True → un seul .mp4 ; False → archive .zip")
    status:      str  = Field(description="pending | downloading | ready | error")


class JobStatus(BaseModel):
    """État en temps réel d'un job de téléchargement."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "status": "downloading",
        "progress": 61,
        "current": "Naruto - Saison 1 VOSTFR - Episode 02",
        "dl_bytes": 245366784,
        "dl_total": 402653184,
        "dl_speed": 3145728.0,
        "dl_eta": 50,
        "output_name": "Naruto - Saison 1 VOSTFR.zip",
        "is_single": False,
        "nb_items": 3,
        "error": "",
        "ready": False,
    }})

    job_id:      str   = Field(description="Identifiant unique du job")
    status:      str   = Field(description="pending | downloading | ready | error")
    progress:    int   = Field(description="Progression globale en pourcentage (0–100)")
    current:     str   = Field(default="", description="Nom du fichier actuellement téléchargé")
    dl_bytes:    int   = Field(default=0, description="Octets téléchargés pour le fichier courant")
    dl_total:    int   = Field(default=0, description="Taille totale estimée du fichier courant (octets)")
    dl_speed:    float = Field(default=0.0, description="Vitesse de téléchargement en octets/seconde")
    dl_eta:      int   = Field(default=0, description="Temps restant estimé en secondes")
    output_name: str   = Field(description="Nom du fichier final produit")
    is_single:   bool  = Field(description="True → .mp4 ; False → .zip")
    nb_items:    int   = Field(description="Nombre total d'éléments dans ce job")
    error:       str   = Field(default="", description="Message d'erreur si status == 'error'")
    ready:       bool  = Field(description="True quand le fichier est prêt à être téléchargé")


# ══════════════════════════════════════════════════════════════════════════════
#  PLANNING
# ══════════════════════════════════════════════════════════════════════════════

class AnimeJour(BaseModel):
    titre:       str           = Field(description="Titre de l'animé")
    slug:        Optional[str] = Field(default=None, description="Slug du catalogue")
    url:         Optional[str] = Field(default=None)
    url_saison:  Optional[str] = Field(default=None)
    image:       Optional[str] = Field(default=None)
    heure:       Optional[str] = Field(default=None, description="Heure de diffusion (ex: '17h00')")
    saison_info: Optional[str] = Field(default=None, description="Info saison (ex: 'Saison 2, Ép. 8')")
    lang:        Optional[str] = Field(default=None, description="Langue : vostfr | vf | …")


class PlanningJour(BaseModel):
    """Planning d'un jour de la semaine."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "jour": "Lundi",
        "date": "23/06",
        "animes": [
            {
                "titre": "Kimetsu no Yaiba",
                "slug": "kimetsu-no-yaiba",
                "url": "https://anime-sama.to/catalogue/kimetsu-no-yaiba/",
                "url_saison": "https://anime-sama.to/catalogue/kimetsu-no-yaiba/saison4/vostfr/",
                "image": "https://cdn.anime-sama.fr/s2/illus/kimetsu-no-yaiba.jpg",
                "heure": "17h00",
                "saison_info": "Saison 4, Ép. 11",
                "lang": "vostfr",
            }
        ],
    }})

    jour:   str           = Field(description="Nom du jour (Lundi, Mardi…)")
    date:   Optional[str] = Field(default=None, description="Date courte (ex: '23/06')")
    animes: list[AnimeJour] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
#  GROUPES
# ══════════════════════════════════════════════════════════════════════════════

class GroupResponse(BaseModel):
    """Groupe d'utilisateurs avec ses permissions."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "664f1a2b3c4d5e6f7a8b9c0d",
        "name": "Abonnés Premium",
        "type": "permission",
        "description": "Accès sync + téléchargement illimité",
        "catalogue_slugs": [],
        "genres": [],
        "permissions": {
            "can_sync": True, "can_delete": False, "can_refresh": True,
            "can_download": True, "download_forbidden_slugs": [],
            "download_quota": {"enabled": False},
            "quota": {"enabled": False, "period": "month", "max_syncs": 10},
        },
        "member_count": 42,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-06-01T12:00:00",
    }})

    id:              str           = Field(description="Identifiant MongoDB")
    name:            str
    type:            str           = Field(description="catalogue | genre | permission")
    description:     Optional[str] = Field(default=None)
    catalogue_slugs: list[str]     = Field(default_factory=list, description="Slugs accessibles (groupe de type 'catalogue')")
    genres:          list[str]     = Field(default_factory=list, description="Genres accessibles (groupe de type 'genre')")
    permissions:     dict          = Field(default_factory=dict)
    member_count:    int           = Field(default=0, description="Nombre de membres")
    created_at:      Optional[str] = Field(default=None)
    updated_at:      Optional[str] = Field(default=None)


class MemberAdded(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "ok": True, "username": "alice", "group_id": "664f1a2b3c4d5e6f7a8b9c0d",
    }})
    ok:       bool
    username: str
    group_id: str


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATIONS API (clients)
# ══════════════════════════════════════════════════════════════════════════════

class ClientResponse(BaseModel):
    """Application API (client machine-to-machine)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "client_id": "cli_Xk9mLpQrTvWzYaBcDeFgHi",
        "name": "Bot de synchronisation",
        "description": "Sync automatique nocturne",
        "is_active": True,
        "permissions": {
            "can_sync": True, "can_delete": False, "can_refresh": True,
            "allowed_catalogues": [], "catalogue_content": {},
            "quota": {"enabled": True, "period": "day", "max_syncs": 5},
        },
        "created_at": "2026-06-01T00:00:00",
        "updated_at": "2026-06-21T08:00:00",
    }})

    client_id:   str           = Field(description="Identifiant public de l'application")
    name:        str
    description: Optional[str] = Field(default=None)
    is_active:   bool          = Field(description="False → l'application est bloquée")
    permissions: dict          = Field(default_factory=dict)
    created_at:  Optional[str] = Field(default=None)
    updated_at:  Optional[str] = Field(default=None)


class ClientCreated(ClientResponse):
    """Réponse à la création d'une application — secret affiché une seule fois."""
    model_config = ConfigDict(json_schema_extra={"example": {
        **ClientResponse.model_config["json_schema_extra"]["example"],  # type: ignore[index]
        "client_secret": "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2W3x4Y5z6",
    }})

    client_secret: str = Field(
        description="Secret en clair — affiché une seule fois à la création. Stockez-le immédiatement.",
    )


class SecretRegenerated(BaseModel):
    """Nouveau secret après régénération."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "client_id": "cli_Xk9mLpQrTvWzYaBcDeFgHi",
        "client_secret": "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3i2H1g0F",
    }})
    client_id:     str = Field(description="Identifiant de l'application")
    client_secret: str = Field(description="Nouveau secret en clair — affiché une seule fois")


# ══════════════════════════════════════════════════════════════════════════════
#  SÉCURITÉ
# ══════════════════════════════════════════════════════════════════════════════

class SecurityState(BaseModel):
    """État du verrou global de l'API."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "locked": True,
        "reason": "Maintenance programmée — reprise à 06h00",
        "banned_count": 3,
    }})
    locked:       bool = Field(description="True → tous les non-admins reçoivent 503")
    reason:       str  = Field(default="", description="Message affiché aux utilisateurs bloqués")
    banned_count: int  = Field(default=0, description="Nombre d'IPs actuellement bannies")


class IpBan(BaseModel):
    """Entrée de ban d'adresse IP."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "ip": "192.168.1.42",
        "reason": "Scraping abusif",
        "banned_at": "2026-06-20T22:15:00",
        "banned_by": "admin",
    }})
    ip:        str           = Field(description="Adresse IP bannie")
    reason:    str           = Field(default="", description="Raison du ban")
    banned_at: Optional[str] = Field(default=None, description="Date ISO du ban")
    banned_by: str           = Field(default="admin", description="Qui a banni cette IP")


# ══════════════════════════════════════════════════════════════════════════════
#  TÉLÉCHARGEMENTS (admin)
# ══════════════════════════════════════════════════════════════════════════════

class DownloadRecord(BaseModel):
    """Entrée d'historique de téléchargement."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "username": "alice",
        "slug": "naruto",
        "type": "episode",
        "nb_files": 1,
        "details": "Naruto - Saison 1 VOSTFR - Episode 01.mp4",
        "size_bytes": 196927037,
        "date": "2026-06-20T22:51:33.672548+00:00",
    }})
    username:   str           = Field(description="Utilisateur ayant effectué le téléchargement")
    slug:       str           = Field(description="Slug du catalogue")
    type:       Optional[str] = Field(default=None, description="episode | film | season")
    nb_files:   int           = Field(default=1, description="Nombre de fichiers téléchargés")
    details:    str           = Field(description="Nom du fichier produit")
    size_bytes: Optional[int] = Field(default=None, description="Taille en octets")
    date:       Optional[str] = Field(default=None, description="Date ISO du téléchargement")


class DlQuota(BaseModel):
    """Quota de téléchargement individuel."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "username": "alice",
        "max_files_per_day": 10,
        "max_gb_per_day": 5.0,
        "can_download": True,
    }})
    username:          str   = Field(description="Utilisateur concerné")
    max_files_per_day: int   = Field(description="Nombre max de fichiers par jour")
    max_gb_per_day:    float = Field(description="Volume max en Go par jour")
    can_download:      bool  = Field(default=True, description="False → téléchargement désactivé")


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRAMMATIONS (schedules)
# ══════════════════════════════════════════════════════════════════════════════

class ScheduleResponse(BaseModel):
    """Programmation automatique de synchronisation."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "664f1a2b3c4d5e6f7a8b9c0e",
        "slug": "naruto-shippuden",
        "frequency": "weekly",
        "hour": 2,
        "minute": 0,
        "day_of_week": 0,
        "day_of_month": None,
        "interval_days": None,
        "description": None,
        "active": True,
        "last_run": None,
        "next_run": "2026-06-22T02:00:00+00:00",
        "created_at": "2026-06-21T16:35:05+00:00",
        "updated_at": "2026-06-21T16:35:05+00:00",
    }})
    id:             str           = Field(description="Identifiant MongoDB")
    slug:           str           = Field(description="Slug du catalogue à synchroniser")
    frequency:      str           = Field(description="daily | weekly | monthly | interval")
    hour:           int           = Field(description="Heure d'exécution (0-23)")
    minute:         int           = Field(default=0, description="Minute d'exécution (0-59)")
    day_of_week:    Optional[int] = Field(default=None, description="0=lundi … 6=dimanche (weekly)")
    day_of_month:   Optional[int] = Field(default=None, description="Jour du mois (monthly)")
    interval_days:  Optional[int] = Field(default=None, description="Intervalle en jours (interval)")
    description:    Optional[str] = Field(default=None)
    active:         bool          = Field(description="False → programmation désactivée")
    last_run:       Optional[str] = Field(default=None, description="Date ISO de la dernière exécution")
    next_run:       Optional[str] = Field(default=None, description="Date ISO de la prochaine exécution")
    created_at:     Optional[str] = Field(default=None)
    updated_at:     Optional[str] = Field(default=None)


# ══════════════════════════════════════════════════════════════════════════════
#  GÉNÉRIQUES
# ══════════════════════════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"message": "Mise à jour lancée en arrière-plan"}})
    message: str


class OkResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ok": True}})
    ok: bool = True


class StatusStarted(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "started", "slug": "naruto",
    }})
    status:  str           = Field(description="Toujours 'started'")
    slug:    Optional[str] = Field(default=None)
    message: Optional[str] = Field(default=None)


class BulkResult(BaseModel):
    """Résultat d'une opération groupée sur plusieurs catalogues."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "ok":     ["naruto", "bleach"],
        "errors": {"one-piece": "Introuvable"},
    }})
    ok:     list[str]     = Field(default_factory=list, description="Slugs traités avec succès")
    errors: dict[str, str] = Field(default_factory=dict, description="slug → message d'erreur")


class EnrichmentResult(BaseModel):
    """Résultat d'un déclenchement d'enrichissement AniList (admin)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "ok":     ["naruto", "one-piece"],
        "errors": {"obscure-manga": "Aucun résultat AniList"},
    }})
    ok:     list[str]      = Field(default_factory=list, description="Slugs enrichis avec succès")
    errors: dict[str, str] = Field(default_factory=dict, description="slug → raison de l'échec")


class NeedsReviewItem(BaseModel):
    """Catalogue dont l'appariement AniList est incertain (confiance < 0.7)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "slug": "some-obscure-title", "nom": "Some Obscure Title",
        "type_contenu": "anime",
        "anilist_id": 12345, "match_confidence": 0.42,
    }})
    slug:             str
    nom:              str
    type_contenu:     str
    anilist_id:       Optional[int]   = None
    match_confidence: Optional[float] = None


class EnrichmentCorrection(BaseModel):
    """Corps de requête pour forcer manuellement un anilist_id sur un catalogue."""
    model_config = ConfigDict(json_schema_extra={"example": {"anilist_id": 21}})
    anilist_id: int = Field(description="ID AniList correct à appliquer")
