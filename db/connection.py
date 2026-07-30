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
        db  = get_db()
        col = db["catalogues"]

        await col.create_index("slug",        unique=True)
        await col.create_index("etat")
        await col.create_index("type_contenu")
        await col.create_index("genres")
        await col.create_index("langues")
        await col.create_index("enrichment.enriched_at")
        await col.create_index("enrichment.needs_review")

        # L'index texte peut entrer en conflit avec un ancien index (ex: "name_text").
        # On supprime l'ancien avant de recréer.
        try:
            await col.create_index([("nom", "text"), ("titre_alternatif", "text")])
        except OperationFailure as e:
            if e.code == 85:  # IndexOptionsConflict
                logger.warning("Index texte en conflit — suppression de l'ancien index texte.")
                try:
                    existing = await col.index_information()
                    for name, info in existing.items():
                        if info.get("key", {}).get("_fts") == "text":
                            await col.drop_index(name)
                            logger.info(f"Ancien index texte '{name}' supprimé.")
                    await col.create_index([("nom", "text"), ("titre_alternatif", "text")])
                except Exception as inner_e:
                    logger.warning(f"Impossible de recréer l'index texte : {inner_e}")
            else:
                raise

        # Index sur la collection users
        await db["users"].create_index("username", unique=True)
        await db["users"].create_index("oidc_sub")
        await db["users"].create_index("groups")

        # Index sur les groupes
        await db["groups"].create_index("name")

        # Index access_logs — recherche + TTL 90 jours
        await db["access_logs"].create_index("timestamp")
        await db["access_logs"].create_index("ip")
        await db["access_logs"].create_index("username")
        await db["access_logs"].create_index(
            "expires_at",
            expireAfterSeconds=0,  # TTL : expire à la date stockée dans expires_at
        )

        logger.info("Index MongoDB créés")

    except OperationFailure as e:
        logger.warning(f"Index MongoDB — erreur d'authentification ou de droits : {e}")
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.warning(f"Impossible de créer les index MongoDB : {e}")
