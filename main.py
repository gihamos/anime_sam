from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.logger import logger
from db.connection import setup_indexes
from api.routes.catalogues import router as catalogues_router
from api.routes.planning import router as planning_router
from services.catalogue_service import mettre_a_jour_tous

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_indexes()
    scheduler.add_job(mettre_a_jour_tous, "interval", hours=24, id="auto_update")
    scheduler.start()
    logger.info("Démarrage de l'application")
    yield
    scheduler.shutdown()
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="Anime Sama API",
    version="2.0",
    description=(
        "API de scraping et catalogue pour anime-sama.to.\n\n"
        "## Flux d'utilisation\n"
        "1. **Recherche** : `GET /catalogues/rechercher?q=naruto`\n"
        "2. **Catalogue** : `GET /catalogues/naruto` (scrape si absent en DB)\n"
        "3. **Épisodes** : `POST /catalogues/naruto/sync-episodes` (fond)\n"
        "4. **Planning** : `GET /planning/`\n"
    ),
    lifespan=lifespan,
)

app.include_router(catalogues_router)
app.include_router(planning_router)


@app.get("/", tags=["Root"])
def home():
    return {
        "message":  "Anime Sama API opérationnelle",
        "version":  "2.0",
        "docs":     "/docs",
        "endpoints": {
            "recherche":      "/catalogues/rechercher?q=naruto",
            "catalogue":      "/catalogues/{slug}",
            "sync_episodes":  "POST /catalogues/{slug}/sync-episodes",
            "planning":       "/planning/",
        },
    }
