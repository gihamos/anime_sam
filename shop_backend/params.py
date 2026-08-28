import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ── MongoDB — même serveur qu'anime_sama, base logique distincte ───────────
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB  = os.getenv("MONGODB_DB",  "anime_sama_shop")

# ── Authentification JWT — secret indépendant de celui d'anime_sam ─────────
# Ne JAMAIS réutiliser le JWT_SECRET d'anime_sam : les tokens des deux
# systèmes doivent rester strictement non interchangeables.
SHOP_JWT_SECRET              = os.getenv("SHOP_JWT_SECRET",              "changeme-shop-secret-in-env")
SHOP_JWT_EXPIRE_MINUTES      = int(os.getenv("SHOP_JWT_EXPIRE_MINUTES",      "1440"))  # 24 h
SHOP_JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("SHOP_JWT_REFRESH_EXPIRE_DAYS", "30"))

# Compte admin créé automatiquement au démarrage si aucun compte n'existe.
SHOP_ADMIN_USERNAME = os.getenv("SHOP_ADMIN_USERNAME", "admin")
SHOP_ADMIN_PASSWORD = os.getenv("SHOP_ADMIN_PASSWORD", "admin")

SHOP_PORT = int(os.getenv("SHOP_PORT", "8010"))

# ── Jellyfin (provisioning des comptes clients) ─────────────────────────────
JELLYFIN_BASE_URL = os.getenv("JELLYFIN_BASE_URL", "http://jellyfin:8096")
JELLYFIN_API_KEY  = os.getenv("JELLYFIN_API_KEY",  "")

# ── PayPal (abonnements récurrents) ─────────────────────────────────────────
PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID",     "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID    = os.getenv("PAYPAL_WEBHOOK_ID",    "")
PAYPAL_API_BASE      = os.getenv("PAYPAL_API_BASE",      "https://api-m.sandbox.paypal.com")

# URLs de retour après approbation PayPal — pointent vers shop_app.
SHOP_PUBLIC_URL       = os.getenv("SHOP_PUBLIC_URL", "http://localhost:5173")
PAYPAL_RETURN_URL     = os.getenv("PAYPAL_RETURN_URL", f"{SHOP_PUBLIC_URL}/compte/paiement/retour")
PAYPAL_CANCEL_URL     = os.getenv("PAYPAL_CANCEL_URL", f"{SHOP_PUBLIC_URL}/compte/paiement/annule")

# ── API anime_sam — SEULE dépendance volontaire vers l'autre système, réservée au
# raccourci "Synchroniser Jellyfin" de l'admin boutique (décision explicite : shop_backend
# reste sinon totalement indépendant, voir le plan de commercialisation). Identifiants d'un
# compte admin anime_sam dédié, distincts de SHOP_ADMIN_USERNAME/PASSWORD ci-dessus — à
# renseigner dans .env, aucune valeur par défaut correcte n'existant pour un mot de passe.
ANIME_SAM_API_URL       = os.getenv("ANIME_SAM_API_URL", "http://anime_sama:8000")
ANIME_SAM_ADMIN_USERNAME = os.getenv("ANIME_SAM_ADMIN_USERNAME", "")
ANIME_SAM_ADMIN_PASSWORD = os.getenv("ANIME_SAM_ADMIN_PASSWORD", "")
