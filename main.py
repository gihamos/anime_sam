from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import logger
from db.connection import setup_indexes
from api.routes.catalogues import router as catalogues_router
from api.routes.planning import router as planning_router
from api.routes.auth import router as auth_router
from api.routes.admin import router as admin_router
from api.routes.groups import router as groups_router
from services.catalogue_service import mettre_a_jour_tous
from services.scheduler_service import scheduler, load_schedules_from_db
from params import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_PORT


async def _create_default_admin() -> None:
    """Crée le compte admin par défaut si aucun utilisateur n'existe en DB."""
    from db.user_repository import count_users, create_user
    from api.dependencies import hash_password
    from models.user import Role

    if await count_users() > 0:
        return

    await create_user({
        "username":        ADMIN_USERNAME,
        "email":           None,
        "role":            Role.ADMIN,
        "hashed_password": hash_password(ADMIN_PASSWORD),
        "is_active":       True,
        "is_blocked":      False,
        "permissions": {
            "can_sync":           True,
            "can_delete":         True,
            "can_refresh":        True,
            "allowed_catalogues": [],
            "catalogue_content":  {},
            "quota":              {"enabled": False, "period": "month", "max_syncs": 10},
        },
    })
    logger.info(
        f"Compte admin créé → username='{ADMIN_USERNAME}' "
        f"(modifiez ADMIN_USERNAME/ADMIN_PASSWORD dans .env)"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_indexes()
    await _create_default_admin()

    # Sync auto quotidienne (mise à jour des métadonnées)
    scheduler.add_job(
        mettre_a_jour_tous,
        "interval",
        hours=24,
        id="auto_update_metadata",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()

    # Charger les programmations de sync depuis la DB
    await load_schedules_from_db()

    logger.info("Démarrage de l'application")
    yield
    scheduler.shutdown()
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="Anime Sama API",
    version="2.0",
    description=(
        "API de scraping et catalogue pour anime-sama.to.\n\n"
        "## Authentification\n"
        "Routes protégées : utiliser le bouton **Authorize** avec `username` / `password`.\n\n"
        "## Flux d'utilisation\n"
        "1. **Login** : `POST /auth/login`\n"
        "2. **Recherche** : `GET /catalogues/rechercher?q=naruto`\n"
        "3. **Catalogue** : `GET /catalogues/naruto` (scrape si absent en DB)\n"
        "4. **Sync** : `POST /catalogues/naruto/sync-content` (authentifié)\n"
        "5. **Planning** : `GET /planning/`\n"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{ADMIN_PORT}", f"http://127.0.0.1:{ADMIN_PORT}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(groups_router)
app.include_router(catalogues_router)
app.include_router(planning_router)


@app.get("/", tags=["Root"])
def home():
    return {
        "message":  "Anime Sama API opérationnelle",
        "version":  "2.0",
        "docs":     "/docs",
        "endpoints": {
            "login":      "POST /auth/login",
            "recherche":  "/catalogues/rechercher?q=naruto",
            "catalogue":  "/catalogues/{slug}",
            "sync":       "POST /catalogues/{slug}/sync-content",
            "planning":   "/planning/",
        },
    }
