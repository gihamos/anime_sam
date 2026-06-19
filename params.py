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
JWT_SECRET          = os.getenv("JWT_SECRET",         "7fec5aa449ceea4967ab78f52063fff3247adf8d91f204a612339c2366daea74")
JWT_EXPIRE_MINUTES  = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 h par défaut

# Compte admin créé automatiquement au démarrage si aucun utilisateur n'existe.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")