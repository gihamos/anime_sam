import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent

BASE_SAMA_URL    = os.getenv("BASE_SAMA_URL", "https://anime-sama.to/")
MONGODB_URL      = os.getenv("MONGODB_URL",   "mongodb://localhost:27017")
MONGODB_DB       = os.getenv("MONGODB_DB",    "anime_sama")

# Proxy optionnel pour Playwright (bypass FortiGuard ou autres filtres réseau)
# Format : http://user:pass@host:port  ou  socks5://host:port
PLAYWRIGHT_PROXY = os.getenv("PLAYWRIGHT_PROXY", "")

# --- Authentification JWT ---
# Clé secrète pour signer les tokens. Changer OBLIGATOIREMENT en production.
JWT_SECRET               = os.getenv("JWT_SECRET",              "7fec5aa449ceea4967ab78f52063fff3247adf8d91f204a612339c2366daea74")
JWT_EXPIRE_MINUTES       = int(os.getenv("JWT_EXPIRE_MINUTES",       "1440"))   # 24 h par défaut
JWT_REFRESH_EXPIRE_DAYS  = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS",  "30"))     # 30 jours

# Compte admin créé automatiquement au démarrage si aucun utilisateur n'existe.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

API_PORT   = int(os.getenv("API_PORT",   "8000"))
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8001"))

# ── OpenID Connect ──────────────────────────────────────────────────────────
# URL de callback que le fournisseur OIDC doit avoir en liste blanche.
OIDC_CALLBACK_URL   = os.getenv("OIDC_CALLBACK_URL",   f"http://localhost:8000/auth/oidc/callback")
# URL vers laquelle le backend redirige après une connexion OIDC réussie.
OIDC_ADMIN_REDIRECT = os.getenv("OIDC_ADMIN_REDIRECT", f"http://localhost:8001")

_raw_providers: dict[str, dict] = {
    "google": {
        "client_id":     os.getenv("OIDC_GOOGLE_CLIENT_ID",     ""),
        "client_secret": os.getenv("OIDC_GOOGLE_CLIENT_SECRET", ""),
        "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
        "name":          "Google",
        "scopes":        ["openid", "email", "profile"],
    },
    "github": {
        "client_id":     os.getenv("OIDC_GITHUB_CLIENT_ID",     ""),
        "client_secret": os.getenv("OIDC_GITHUB_CLIENT_SECRET", ""),
        "name":          "GitHub",
    },
    "custom": {
        "client_id":     os.getenv("OIDC_CUSTOM_CLIENT_ID",     ""),
        "client_secret": os.getenv("OIDC_CUSTOM_CLIENT_SECRET", ""),
        "discovery_url": os.getenv("OIDC_CUSTOM_DISCOVERY_URL", ""),
        "name":          os.getenv("OIDC_CUSTOM_NAME",          "SSO"),
        "scopes":        ["openid", "email", "profile"],
    },
}
# Ne garder que les fournisseurs ayant un client_id configuré
OIDC_PROVIDERS: dict[str, dict] = {
    k: v for k, v in _raw_providers.items() if v.get("client_id")
}

# ── AniList / DeepL (enrichissement métadonnées) ────────────────────────────
ANILIST_API_URL             = os.getenv("ANILIST_API_URL", "https://graphql.anilist.co")
ANILIST_RATE_LIMIT_PER_MIN  = int(os.getenv("ANILIST_RATE_LIMIT_PER_MIN", "90"))
ANILIST_ENRICHMENT_ENABLED  = os.getenv("ANILIST_ENRICHMENT_ENABLED", "true").lower() == "true"
DEEPL_API_KEY                = os.getenv("DEEPL_API_KEY", "")
DEEPL_API_URL                = os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")