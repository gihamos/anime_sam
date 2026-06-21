# Anime Sama — API & Interface d'administration

Plateforme de scraping et de gestion de catalogues pour **anime-sama.to**.  
Permet de rechercher, synchroniser, planifier et télécharger des contenus anime/manga depuis une interface web ou une API REST.

---

## Fonctionnalités

- **Catalogue** — recherche, synchronisation des épisodes/chapitres, mise à jour automatique
- **Téléchargements** — via yt-dlp avec suivi de progression en temps réel, annulation, quotas par groupe
- **Planification** — synchronisations automatiques programmées par titre
- **Gestion des utilisateurs** — rôles (admin/user/client), permissions granulaires, groupes
- **Groupes** — par catalogue, par genre ou par permission ; quotas de sync et de téléchargement
- **Sécurité** — ban d'adresses IP, verrouillage total de l'API avec bypass admin, middleware JWT
- **OIDC** — connexion via Google, GitHub ou un fournisseur SSO personnalisé
- **Interface admin** — SPA sur port 8001, thème clair/sombre, sans framework JavaScript

---

## Prérequis

| Outil | Version minimale |
|---|---|
| Python | 3.12 |
| MongoDB | 7 |
| ffmpeg | toute version récente |
| Playwright Chromium | installé via `playwright install chromium` |

---

## Installation locale

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd anime_sam

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt
playwright install chromium

# 4. Configurer l'environnement
cp .env.example .env             # puis éditer .env

# 5. Lancer (API + Admin en parallèle)
python start.py
```

**Accès :**
- API + docs Swagger : http://localhost:8000/docs  
- Interface admin : http://localhost:8001

---

## Configuration (`.env`)

```ini
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=anime_sama

# JWT
JWT_SECRET=changez-cette-valeur-en-production
JWT_EXPIRE_MINUTES=1440

# Compte admin créé automatiquement au premier démarrage
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# Ports
API_PORT=8000
ADMIN_PORT=8001

# URL de base du site scrappé
BASE_SAMA_URL=https://anime-sama.to/

# Proxy optionnel pour Playwright (bypass FortiGuard, etc.)
# PLAYWRIGHT_PROXY=http://user:pass@host:port

# OIDC (optionnel)
# OIDC_GOOGLE_CLIENT_ID=
# OIDC_GOOGLE_CLIENT_SECRET=
# OIDC_GITHUB_CLIENT_ID=
# OIDC_GITHUB_CLIENT_SECRET=
```

---

## Docker

### Démarrage rapide

```bash
# Copier et adapter la configuration
cp .env.example .env

# Construire et démarrer tous les services
docker compose up -d

# Voir les logs
docker compose logs -f api
docker compose logs -f admin
```

**Services démarrés :**
| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Interface admin | http://localhost:8001 |
| MongoDB | localhost:27017 |

### Build seul

```bash
docker build -t anime-sama .

# Lancer l'API
docker run -p 8000:8000 --env-file .env anime-sama

# Lancer l'admin
docker run -p 8001:8001 --env-file .env anime-sama python admin_main.py
```

---

## Structure du projet

```
anime_sam/
├── main.py               # Serveur API FastAPI (port 8000)
├── admin_main.py         # Interface admin FastAPI (port 8001)
├── start.py              # Script de lancement local (API + admin)
├── cli.py                # CLI Typer pour accès en ligne de commande
├── params.py             # Configuration (env vars)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── api/
│   ├── routes/           # Endpoints REST (catalogues, auth, admin, download…)
│   └── dependencies.py   # Auth JWT, permissions effectives, groupes
├── db/
│   ├── repository.py     # CRUD catalogues (Motor/MongoDB)
│   ├── user_repository.py
│   ├── groups_repository.py
│   ├── ip_bans_repository.py
│   └── settings_repository.py
├── models/               # Schémas Pydantic
├── services/
│   ├── catalogue_service.py
│   ├── downloader.py     # yt-dlp + annulation + progression
│   ├── scheduler_service.py
│   ├── sync_manager.py
│   └── api_guard.py      # Verrouillage global de l'API
└── utils/
    └── logger.py
```

---

## API — aperçu des routes principales

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/auth/login` | Authentification (retourne JWT) |
| `GET` | `/catalogues/rechercher?q=naruto` | Recherche en DB |
| `GET` | `/catalogues/{slug}` | Catalogue complet |
| `POST` | `/catalogues/{slug}/sync-content` | Synchronise épisodes/chapitres |
| `GET` | `/planning/` | Planning hebdomadaire |
| `POST` | `/download/jobs` | Créer un téléchargement |
| `GET` | `/download/jobs/{id}` | État et progression |
| `DELETE` | `/download/jobs/{id}` | Annuler un téléchargement |
| `GET` | `/admin/users` | Liste des utilisateurs (admin) |
| `GET` | `/admin/api/security/state` | État du verrou API (admin) |
| `PUT` | `/admin/api/security/lock` | Verrouiller/déverrouiller l'API (admin) |
| `POST` | `/admin/api/security/ip-bans` | Bannir une IP (admin) |

Documentation interactive complète : http://localhost:8000/docs

---

## Visibilité des catalogues

Par défaut, tout catalogue créé est **privé** (`is_public: false`).  
Un administrateur peut le rendre public depuis l'interface admin (onglet Catalogues → modifier la visibilité).

---

## Licence

Usage privé. Projet non officiel, sans affiliation avec anime-sama.to.
