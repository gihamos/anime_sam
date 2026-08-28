from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from params import MONGODB_URL, MONGODB_DB

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not (MONGODB_URL.startswith("mongodb://") or MONGODB_URL.startswith("mongodb+srv://")):
            raise ValueError(
                f"MONGODB_URL invalide : '{MONGODB_URL}'. "
                "Doit commencer par 'mongodb://' ou 'mongodb+srv://'."
            )
        _client = AsyncIOMotorClient(MONGODB_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[MONGODB_DB]


async def setup_indexes():
    from utils.logger import logger
    from pymongo.errors import OperationFailure

    try:
        db = get_db()

        await db["customers"].create_index("username", unique=True)
        await db["customers"].create_index("email")

        await db["plans"].create_index("slug", unique=True)
        await db["plans"].create_index("is_active")

        await db["subscriptions"].create_index("username")
        await db["subscriptions"].create_index("status")
        await db["subscriptions"].create_index(
            "provider_subscription_id", unique=True, sparse=True,
        )

        await db["payments"].create_index("username")
        await db["payments"].create_index("subscription_id")
        await db["payments"].create_index(
            "provider_payment_id", unique=True, sparse=True,
        )

        await db["tickets"].create_index("username")
        await db["tickets"].create_index("status")

        await db["webhook_events"].create_index(
            [("provider", 1), ("event_id", 1)], unique=True,
        )

        await db["promotions"].create_index("code", unique=True)

        logger.info("shop_backend : index MongoDB créés")

    except OperationFailure as e:
        logger.warning(f"shop_backend : erreur d'authentification/droits sur les index — {e}")
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.warning(f"shop_backend : impossible de créer les index MongoDB — {e}")
