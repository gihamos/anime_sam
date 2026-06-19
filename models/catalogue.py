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
# Catalogue principal
# ---------------------------------------------------------------------------

class Catalogue(BaseModel):
    """
    Représente un catalogue complet sur anime-sama.to.
    Correspond à un document MongoDB dans la collection 'catalogues'.
    """
    slug:              str
    url:               str

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

    metadata:          dict             = Field(default_factory=dict)
    episodes_synced:   bool             = False

    created_at:        Optional[str]    = None
    updated_at:        Optional[str]    = None
