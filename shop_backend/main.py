from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.logger import logger
from db.connection import setup_indexes
from api.routes.auth import router as auth_router
from api.routes.billing import router as billing_router
from api.routes.tickets import router as tickets_router
from api.routes.admin import router as admin_router
from params import SHOP_ADMIN_USERNAME, SHOP_ADMIN_PASSWORD

scheduler = AsyncIOScheduler()


async def _create_default_admin() -> None:
    """Crée le compte admin de la boutique par défaut si aucun compte n'existe."""
    from db.customers_repository import count_customers, create_customer
    from api.dependencies import hash_password
    from models.customer import Role
    from datetime import datetime, timezone

    if await count_customers() > 0:
        return

    await create_customer({
        "username":        SHOP_ADMIN_USERNAME,
        "email":            None,
        "role":             Role.ADMIN,
        "hashed_password":  hash_password(SHOP_ADMIN_PASSWORD),
        "is_active":        True,
        "created_at":       datetime.now(timezone.utc).isoformat(),
    })
    logger.info(
        f"shop_backend : compte admin créé → username='{SHOP_ADMIN_USERNAME}' "
        f"(modifiez SHOP_ADMIN_USERNAME/SHOP_ADMIN_PASSWORD dans .env)"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_indexes()
    await _create_default_admin()

    from services.billing_service import disable_expired_cancellations, cleanup_stale_pending_subscriptions
    scheduler.add_job(
        disable_expired_cancellations,
        "interval",
        hours=24,
        id="disable_expired_cancellations",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        cleanup_stale_pending_subscriptions,
        "interval",
        hours=24,
        id="cleanup_stale_pending_subscriptions",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()

    import services.jellyfin_auto_sync as jellyfin_auto_sync
    jellyfin_auto_sync.init(scheduler)
    await jellyfin_auto_sync.start()

    logger.info("shop_backend : démarrage")
    yield
    scheduler.shutdown()
    logger.info("shop_backend : arrêt")


app = FastAPI(
    title="Anime Sama · Boutique Jellyfin",
    version="1.0",
    description=(
        "Service autonome de gestion des comptes clients, abonnements et paliers "
        "d'accès au serveur Jellyfin. Totalement indépendant de l'API anime_sam "
        "(auth, base de données et tokens distincts)."
    ),
    docs_url=None,
    redoc_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(tickets_router)
app.include_router(admin_router)


@app.get("/api/health", tags=["Root"])
def health():
    return {"message": "shop_backend opérationnel", "version": "1.0", "docs": "/docs"}


# ---------------------------------------------------------------------------
# shop_app (build statique) — servi par ce même process, déclaré en dernier pour ne
# jamais intercepter les routes API ci-dessus. Même pattern qu'admin_main.py :
# /assets monté séparément, catch-all explicite qui renvoie index.html pour toute
# route côté client (React Router) — StaticFiles(html=True) seul ne suffit pas pour
# ce fallback (vérifié : renvoie 404 sur les sous-routes comme /compte).
# ---------------------------------------------------------------------------

_SHOP_APP_DIST = Path(__file__).parent / "shop_app_dist"

if _SHOP_APP_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_SHOP_APP_DIST / "assets"), name="shop-assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def shop_favicon():
        return FileResponse(_SHOP_APP_DIST / "favicon.svg")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def shop_spa(full_path: str):
        """Fallback SPA : toute route côté client (React Router) sert index.html."""
        return HTMLResponse(
            (_SHOP_APP_DIST / "index.html").read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma":        "no-cache",
            },
        )
