"""
Routes REST pour le planning anime-sama.

GET /planning/   → planning de la semaine en cours
"""

from fastapi import APIRouter, HTTPException
from services.scraper import get_planning
from models.responses import PlanningJour

router = APIRouter(prefix="/planning", tags=["Planning"])


@router.get("/", response_model=list[PlanningJour], summary="Planning de la semaine")
async def get_planning_route():
    """
    Retourne le planning de diffusion de la semaine en cours.
    Source : https://anime-sama.to/planning/  (HTML statique, rapide)

    Structure :
    ```json
    [
      {
        "jour": "Lundi",
        "date": "15/06",
        "animes": [
          {
            "titre": "Rick et Morty",
            "slug": "rick-et-morty",
            "url": "https://anime-sama.to/catalogue/rick-et-morty/",
            "url_saison": "https://anime-sama.to/catalogue/rick-et-morty/saison9/vostfr/",
            "image": "…",
            "heure": "12h00",
            "saison_info": "Saison 9",
            "lang": "vostfr"
          }
        ]
      }
    ]
    ```
    """
    planning = await get_planning()
    if not planning:
        raise HTTPException(status_code=503, detail="Impossible de récupérer le planning")
    return planning
