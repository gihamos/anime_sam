"""
Modèles de données pour anime-sama.to.

Hiérarchie :
  Catalogue
    ├─ saisons  : list[Saison]    → épisodes avec lecteurs vidéo
    ├─ films    : list[Film]      → lecteurs vidéo directs
    └─ scans    : list[Scan]      → chapitres (parsing non encore implémenté)

La récupération d'un catalogue se fait en deux temps :
  1. Structure  (getcatalogue)      → rapide  (~5 s)
  2. Épisodes   (sync_episodes)     → lent    (~2-30 min selon l'animé)

Le champ `episodes_synced` indique si les épisodes ont été chargés.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Énumérations
# ---------------------------------------------------------------------------

class Etat(str, Enum):
    TERMINE   = "termine"
    EN_COURS  = "en_cours"
    ABANDONNE = "abandonne"


class TypeContenu(str, Enum):
    ANIME = "anime"
    SCAN  = "scan"
    FILM  = "film"
    SERIE = "serie"
    AUTRE = "autre"


# ---------------------------------------------------------------------------
# Sous-modèles vidéo / épisode
# ---------------------------------------------------------------------------

class Video(BaseModel):
    """Un lecteur vidéo pour un épisode ou un film."""
    lecteur:    str            = ""
    player_url: Optional[str] = None


class Episode(BaseModel):
    """Un épisode d'une saison."""
    numero: int
    titre:  Optional[str]     = None
    videos: list[Video]       = Field(default_factory=list)
    # Métadonnées AniList par épisode (titre/vignette via streamingEpisodes) — best-effort,
    # dispo seulement pour les séries avec partenariat streaming listé sur AniList.
    enrichment: dict          = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Contenus d'un catalogue
# ---------------------------------------------------------------------------

class Saison(BaseModel):
    """
    Une saison (ou arc, ou version) d'un animé.
    Le slug est extrait de l'URL : /catalogue/naruto/saison1/vostfr/ → "saison1".
    """
    nom:            str
    slug:           str
    lang:           str            = "vostfr"
    url:            str
    image:          Optional[str]  = None
    total_episodes: int            = 0
    episodes:       list[Episode]  = Field(default_factory=list)


class Film(BaseModel):
    """
    Un film. Les vidéos correspondent aux lecteurs disponibles.
    slug ex : "film1", "film-tv-1"
    """
    nom:    str
    slug:   str
    lang:   str            = "vostfr"
    url:    str
    image:  Optional[str]  = None
    videos: list[Video]    = Field(default_factory=list)
    # Enrichissement AniList individuel — un catalogue "film" peut contenir plusieurs
    # films distincts (franchise), chacun apparié séparément (pas au niveau catalogue).
    enrichment: dict        = Field(default_factory=dict)


class LecteurScan(BaseModel):
    """Un lecteur/plateforme de lecture pour un chapitre de scan."""
    lecteur:    str            = ""
    player_url: Optional[str] = None


class ChapitreScan(BaseModel):
    """Un chapitre de scan/manga."""
    numero:   float
    titre:    Optional[str]      = None
    url:      str
    lecteurs: list[LecteurScan]  = Field(default_factory=list)
    images:   list[str]          = Field(default_factory=list)


class Scan(BaseModel):
    """Un scan/manga attaché à un catalogue."""
    nom:       str
    slug:      str
    lang:      Optional[str]         = None
    url:       str
    image:     Optional[str]         = None
    chapitres: list[ChapitreScan]    = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Visibilité / contrôle d'accès public d'un catalogue
# ---------------------------------------------------------------------------

class CatalogueVisibility(BaseModel):
    """
    Contrôle ce que les utilisateurs non authentifiés (ou restreints) peuvent voir.
    Pour chaque type de contenu, une liste vide = tout le contenu est visible.
    """
    is_public:      bool      = False  # privé par défaut — activer explicitement dans l'admin
    public_saisons: list[str] = Field(default_factory=list)  # slugs visibles publiquement
    public_films:   list[str] = Field(default_factory=list)
    public_scans:   list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Catalogue principal
# ---------------------------------------------------------------------------

class Catalogue(BaseModel):
    """
    Représente un catalogue complet sur anime-sama.to.
    Correspond à un document MongoDB dans la collection 'catalogues'.
    """
    slug:              str
    url:               str

    # Origine du catalogue — "anime-sama" (scraping historique, défaut pour les documents
    # existants) ou "tmdb-vidzy" (métadonnées TMDB + lecteur Vidzy). Point d'extension pour
    # une future 3e source : chaque route/service qui a besoin de traiter les sources
    # différemment peut brancher dessus sans dupliquer routes/téléchargement/sync Jellyfin.
    source:            str             = "anime-sama"

    nom:               str
    titre_alternatif:  Optional[str]    = None
    synopsis:          Optional[str]    = None
    image:             Optional[str]    = None

    genres:            list[str]        = Field(default_factory=list)
    langues:           list[str]        = Field(default_factory=list)
    etat:              Etat             = Etat.EN_COURS
    type_contenu:      TypeContenu      = TypeContenu.ANIME

    saisons:           list[Saison]     = Field(default_factory=list)
    films:             list[Film]       = Field(default_factory=list)
    scans:             list[Scan]       = Field(default_factory=list)

    visibility:        CatalogueVisibility = Field(default_factory=CatalogueVisibility)
    metadata:          dict             = Field(default_factory=dict)
    # Métadonnées AniList (score, genres_fr, synopsis_fr, cover art…) — volontairement
    # séparé de `metadata` (qui reste les paires brutes scrapées depuis anime-sama.to).
    # Jamais réécrit par le scraping (voir save_catalogue), seulement par le pipeline
    # d'enrichissement.
    enrichment:        dict             = Field(default_factory=dict)
    episodes_synced:   bool             = False

    created_at:        Optional[str]    = None
    updated_at:        Optional[str]    = None
