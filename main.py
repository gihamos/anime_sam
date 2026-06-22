from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from utils.logger import logger
from db.connection import setup_indexes
import db.ip_bans_repository as ip_bans_repo
import services.api_guard as api_guard
from api.routes.catalogues import router as catalogues_router, my_router as mycatalogues_router
from api.routes.planning import router as planning_router
from api.routes.auth import router as auth_router
from api.routes.admin import router as admin_router
from api.routes.groups import router as groups_router
from api.routes.download import router as download_router, admin_router as dl_admin_router
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
    await ip_bans_repo.load()
    await api_guard.load()

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
        "Toutes les routes protégées attendent l'en-tête :\n"
        "`Authorization: Bearer <token>`\n\n"
        "Obtenez un token via `POST /auth/login` (utilisateur) "
        "ou `POST /auth/client-token` (application).\n\n"
        "## Flux d'utilisation\n"
        "1. **Login** : `POST /auth/login`\n"
        "2. **Recherche** : `GET /catalogues/rechercher?q=naruto`\n"
        "3. **Catalogue** : `GET /catalogues/{slug}` (scrape si absent en DB)\n"
        "4. **Sync** : `POST /catalogues/{slug}/sync-content`\n"
        "5. **Planning** : `GET /planning/`\n"
    ),
    # Swagger UI désactivé (permet l'exécution de vraies requêtes)
    # Documentation en lecture seule uniquement via ReDoc
    docs_url=None,
    redoc_url="/docs",
    lifespan=lifespan,
)

_ALWAYS_OPEN = {"/auth/login", "/docs", "/openapi.json", "/"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    ip = (request.client.host if request.client else "") or ""

    # ── Ban IP (vérification en mémoire, O(1)) ────────────────────────────────
    if ip_bans_repo.is_banned(ip):
        return JSONResponse(
            {"detail": "Accès refusé — adresse IP bannie"},
            status_code=403,
        )

    # ── Verrouillage API ──────────────────────────────────────────────────────
    if api_guard.is_locked():
        path = request.url.path
        # Routes toujours accessibles (login admin + routes de déverrouillage)
        if path not in _ALWAYS_OPEN and not path.startswith("/admin/api/security"):
            is_admin = False
            token = (
                request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                or request.query_params.get("token", "")
            )
            if token:
                try:
                    from jose import jwt
                    from params import JWT_SECRET
                    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                    # Les tokens client (applications API) ne sont jamais admin
                    if payload.get("type") != "client":
                        sub = payload.get("sub")
                        if sub:
                            from db.user_repository import find_by_username
                            u = await find_by_username(sub)
                            is_admin = bool(u and u.get("role") == "admin")
                except Exception:
                    pass
            if not is_admin:
                reason = api_guard.get_state()["reason"] or "API temporairement verrouillée — maintenance en cours"
                return JSONResponse({"detail": reason}, status_code=503)

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{ADMIN_PORT}", f"http://127.0.0.1:8082","http://localhost:8082","http://10.237.9.204:8082"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(groups_router)
app.include_router(catalogues_router)
app.include_router(mycatalogues_router)
app.include_router(planning_router)
app.include_router(download_router)
app.include_router(dl_admin_router)


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
