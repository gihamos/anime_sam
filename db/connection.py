from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from params import MONGODB_URL, MONGODB_DB

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not (MONGODB_URL.startswith("mongodb://") or MONGODB_URL.startswith("mongodb+srv://")):
            raise ValueError(
                f"MONGODB_URL invalide dans .env : '{MONGODB_URL}'. "
                "Doit commencer par 'mongodb://' ou 'mongodb+srv://'. "
                "Exemple : mongodb://user:password@localhost:27017/?authSource=admin"
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
        col = db["catalogues"]
        await col.create_index("slug",         unique=True)
        await col.create_index([("nom", "text"), ("titre_alternatif", "text")])
        await col.create_index("etat")
        await col.create_index("type_contenu")
        await col.create_index("genres")
        await col.create_index("langues")
        logger.info("Index MongoDB créés")
    except OperationFailure as e:
        logger.warning(
            f"Impossible de créer les index MongoDB (authentification requise). "
            f"Ajoutez vos credentials dans MONGODB_URL dans .env — {e}"
        )
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.warning(f"Impossible de créer les index MongoDB : {e}")
