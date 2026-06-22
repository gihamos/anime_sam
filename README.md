# Anime Sama — API & Interface d'administration

Plateforme de scraping, de gestion de catalogues et de téléchargements pour **anime-sama.to**.  
API REST (FastAPI) · Interface admin SPA · Application mobile · CLI · Docker

![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47a248?logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ed?logo=docker&logoColor=white)

## Fonctionnalités

- **Catalogue** — scraping automatique depuis anime-sama.to, recherche multi-critères (type, langue, genre, état, année), synchronisation épisodes / chapitres
- **Téléchargements** — via yt-dlp, progression en temps réel (vitesse, ETA, octets), annulation instantanée, ZIP multi-épisodes, quotas par utilisateur et par groupe
- **Planification** — synchronisations automatiques programmées, recherche par titre dans l'interface
- **Utilisateurs & groupes** — rôles `admin` / `user` / `client`, permissions granulaires, blocage temporaire ou permanent, groupes par catalogue / genre / permission
- **Applications API** — clients machine-to-machine avec `client_id` / `client_secret`
- **Sécurité** — ban IP en mémoire O(1), verrou API total (503 sauf admins), historique des connexions avec statistiques d'usage
- **OIDC / SSO** — Google, GitHub, fournisseur personnalisé (discovery URL)
- **Interface admin** — SPA port 8001, thème clair / sombre, sans dépendance JS externe
- **Application mobile** — client Android/iOS dans `mobile_app/`
- **CLI** — toutes les opérations admin disponibles en ligne de commande

## Architecture

```text
┌──────────────────┐              ┌─────────────────────────────┐
│  Interface admin │◄────────────►│   API FastAPI — :8000        │
│  :8001           │              │                             │
└──────────────────┘              │  Middleware                  │
                                  │  • IP ban (cache mémoire)   │
┌──────────────────┐              │  • Verrou API               │
│  App mobile      │◄────────────►│  • CORS                     │
│  React Native    │              │  • Log des accès            │
└──────────────────┘              │                             │
                                  │  Services                   │
┌──────────────────┐              │  • Scraper (Playwright)     │
│  CLI — cli.py    │◄────────────►│  • Downloader (yt-dlp)      │
└──────────────────┘              │  • Scheduler (APScheduler)  │
                                  │  • API Guard                │
                                  └──────────────┬──────────────┘
                                                 │ Motor (async)
                                          ┌──────▼──────┐
                                          │   MongoDB   │
                                          │   :27017    │
                                          └─────────────┘
```

**Collections :** `catalogues` · `users` · `api_clients` · `groups` · `downloads` · `dl_quotas` · `ip_bans` · `settings` · `schedules` · `sync_history` · `usage` · `access_logs`

## Prérequis

- Python ≥ 3.12
- MongoDB ≥ 7
- ffmpeg (requis par yt-dlp)
- Playwright Chromium — `playwright install chromium`

## Installation locale

```bash
git clone <url-du-repo>
cd anime_sam

python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Éditez .env — au minimum JWT_SECRET et ADMIN_PASSWORD
```

## Lancement

```bash
# Tout-en-un (recommandé)
python start.py

# Ou séparément
python main.py          # API :8000
python admin_main.py    # Interface admin :8001
```

| Service | URL |
| --- | --- |
| API REST | <http://localhost:8000> |
| Documentation | <http://localhost:8000/docs> |
| Interface admin | <http://localhost:8001> |

## Configuration

| Variable | Défaut | Description |
| --- | --- | --- |
| `MONGODB_URL` | `mongodb://localhost:27017` | URI de connexion |
| `MONGODB_DB` | `anime_sama` | Nom de la base |
| `JWT_SECRET` | *(valeur de dev)* | **À changer en production** |
| `JWT_EXPIRE_MINUTES` | `1440` | Durée de vie des tokens (24 h) |
| `ADMIN_USERNAME` | `admin` | Compte admin créé au démarrage |
| `ADMIN_PASSWORD` | `admin` | **À changer en production** |
| `API_PORT` | `8000` | Port de l'API |
| `ADMIN_PORT` | `8001` | Port de l'interface admin |
| `BASE_SAMA_URL` | `https://anime-sama.to/` | URL de base du site scrappé |
| `PLAYWRIGHT_PROXY` | *(vide)* | Proxy optionnel pour Playwright |
| `OIDC_GOOGLE_CLIENT_ID` | *(vide)* | OAuth2 Google |
| `OIDC_GITHUB_CLIENT_ID` | *(vide)* | OAuth2 GitHub |
| `OIDC_CUSTOM_DISCOVERY_URL` | *(vide)* | SSO personnalisé — discovery URL OIDC |

## Docker

```bash
cp .env.example .env
docker compose up -d

# Logs
docker compose logs -f api

# Arrêt et suppression des données
docker compose down -v
```

Trois conteneurs : **mongodb**, **api** (:8000) et **admin** (:8001). Les données MongoDB et les fichiers téléchargés sont persistés dans des volumes nommés.

## CLI

La CLI appelle directement les services Python, sans passer par HTTP.

```bash
python cli.py --help
```

### Catalogue

```bash
python cli.py rechercher "naruto"
python cli.py rechercher "dragon" --type anime --lang vostfr --etat en_cours
python cli.py get dragon-ball
python cli.py sync-content dragon-ball
python cli.py saisons naruto
python cli.py films naruto --lang vf
python cli.py episodes naruto saison1 --lang vostfr
python cli.py chapitres naruto 0 --images
python cli.py update-all
python cli.py planning
```

### Utilisateurs

```bash
python cli.py user liste
python cli.py user creer alice motdepasse --role user --email alice@example.com
python cli.py user supprimer alice
python cli.py user bloquer alice --raison "Abus" --jusqu-au 2026-12-31
python cli.py user perms alice --sync --no-delete --no-refresh
python cli.py user quota alice --max 50 --periode month
```

### Groupes

```bash
python cli.py group liste
python cli.py group creer "Abonnés" --type permission
python cli.py group membres <id>
```

### Applications API

```bash
python cli.py app liste
python cli.py app creer "Mon Bot"
python cli.py app regenerer-secret cli_xxxxxxxxxxxx
python cli.py app supprimer cli_xxxxxxxxxxxx
```

### Commandes sécurité

```bash
python cli.py security statut
python cli.py security verrouiller --raison "Maintenance"
python cli.py security deverrouiller
python cli.py security bans
python cli.py security bannir 1.2.3.4 --raison "Scraping abusif"
python cli.py security debannir 1.2.3.4
```

### Téléchargements

```bash
python cli.py dl historique --limit 100
python cli.py dl quotas
python cli.py dl quota-set alice --max-fichiers 10 --max-go 5
```

## API

Documentation complète : **<http://localhost:8000/docs>**

### Authentification

```bash
POST /auth/login          { "username": "...", "password": "..." }
POST /auth/client-token   { "client_id": "...", "client_secret": "..." }
# → { "access_token": "...", "token_type": "bearer" }
```

Toutes les routes protégées attendent `Authorization: Bearer <token>`.

### Routes catalogue

| Méthode | Route | Auth |
| --- | --- | --- |
| `GET` | `/catalogues/` | — |
| `GET` | `/catalogues/rechercher?q=naruto` | — |
| `GET` | `/catalogues/{slug}` | — |
| `POST` | `/catalogues/{slug}/rafraichir` | user |
| `POST` | `/catalogues/{slug}/sync-content` | user |
| `WS` | `/catalogues/{slug}/sync-content/ws` | user |
| `DELETE` | `/catalogues/{slug}` | user |

### Routes téléchargements

| Méthode | Route | Description |
| --- | --- | --- |
| `POST` | `/download/jobs` | Crée un job |
| `GET` | `/download/jobs/{id}` | État, vitesse, ETA |
| `GET` | `/download/jobs/{id}/file` | Récupère le fichier |
| `DELETE` | `/download/jobs/{id}` | Annule / supprime |

### Administration (admin uniquement)

| Méthode | Route | Description |
| --- | --- | --- |
| `GET/PUT` | `/admin/api/catalogues/{slug}` | Métadonnées et visibilité |
| `GET/POST` | `/admin/api/clients` | Applications API |
| `GET/POST` | `/admin/api/groups` | Groupes |
| `POST/DELETE` | `/admin/api/groups/{gid}/members` | Membres |
| `GET/POST` | `/admin/api/schedules` | Planifications |
| `GET/PUT` | `/admin/api/security/lock` | Verrou API |
| `GET/POST` | `/admin/api/security/ip-bans` | Bans IP |
| `DELETE` | `/admin/api/security/ip-bans/{ip}` | Lever un ban |
| `GET` | `/admin/api/access-logs` | Historique des connexions |
| `GET` | `/admin/api/access-logs/stats` | Statistiques d'usage |
| `DELETE` | `/admin/api/access-logs` | Vider l'historique |
| `GET` | `/admin/api/downloads` | Historique des téléchargements |
| `PUT` | `/admin/api/dl-quotas/{username}` | Quota de téléchargement |

## Sécurité

**Ban IP** — stocké en MongoDB et chargé en mémoire au démarrage. Chaque ban / débannissement met à jour les deux. Toutes les requêtes de l'IP sont rejetées avant d'atteindre le routeur.

**Verrou API** — quand actif, tous les utilisateurs reçoivent `503`, sauf les admins (JWT). Les routes `/auth/login` et `/admin/api/security/*` restent toujours accessibles.

**Historique des accès** — chaque requête est journalisée de façon asynchrone (sans impact sur la latence). Les entrées expirent automatiquement après 90 jours via un index TTL MongoDB. Filtrable par IP, utilisateur, date depuis l'interface admin.

## Groupes et permissions

Trois types : `catalogue` (accès à des slugs spécifiques), `genre` (accès par genre), `permission` (droits fonctionnels — sync, delete, refresh, download). Les quotas de téléchargement et de synchronisation sont configurables indépendamment par groupe et par utilisateur.

## OIDC / SSO

```ini
# Google
OIDC_GOOGLE_CLIENT_ID=...
OIDC_GOOGLE_CLIENT_SECRET=...

# GitHub
OIDC_GITHUB_CLIENT_ID=...
OIDC_GITHUB_CLIENT_SECRET=...

# Fournisseur personnalisé (Keycloak, Authentik, etc.)
OIDC_CUSTOM_CLIENT_ID=...
OIDC_CUSTOM_CLIENT_SECRET=...
OIDC_CUSTOM_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration
OIDC_CUSTOM_NAME=Mon SSO

OIDC_CALLBACK_URL=http://localhost:8000/auth/oidc/callback
```

## Structure du projet

```text
anime_sam/
├── main.py                      # API FastAPI — :8000
├── admin_main.py                # Interface admin SPA — :8001
├── start.py                     # Lance API + admin en parallèle
├── cli.py                       # CLI (Typer + Rich)
├── params.py                    # Variables d'environnement
│
├── api/
│   ├── routes/
│   │   ├── auth.py              # Login, profil, OIDC, gestion users
│   │   ├── catalogues.py        # Catalogue, sync, WebSocket
│   │   ├── admin.py             # Clients, planifications, sécurité, logs
│   │   ├── groups.py            # CRUD groupes + membres
│   │   └── download.py          # Jobs + quotas
│   └── dependencies.py          # JWT, permissions, guards
│
├── db/
│   ├── connection.py            # Motor + index MongoDB
│   ├── repository.py            # CRUD catalogues
│   ├── user_repository.py
│   ├── groups_repository.py
│   ├── clients_repository.py
│   ├── downloads_repository.py
│   ├── ip_bans_repository.py    # Cache mémoire + persistence
│   ├── access_log_repository.py # Journalisation des accès (TTL 90j)
│   └── settings_repository.py
│
├── services/
│   ├── catalogue_service.py     # Orchestration scraping + DB
│   ├── downloader.py            # yt-dlp avec annulation et progression
│   ├── scheduler_service.py     # APScheduler
│   ├── sync_manager.py          # Concurrence des syncs
│   ├── scraper.py               # Playwright — anime-sama.to
│   └── api_guard.py             # Verrou API
│
├── models/                      # Schémas Pydantic
└── mobile_app/                  # Client mobile React Native (voir mobile_app/README.md)
```

---

Développé par **Taïse De Thèse Yabie** — [github.com/gihamos](https://github.com/gihamos/)

> Projet non officiel, sans affiliation avec anime-sama.to.
