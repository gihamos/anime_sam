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
# Laisser vide pour connexion directe.
PLAYWRIGHT_PROXY = os.getenv("PLAYWRIGHT_PROXY", "")