# Anime Sama — API & Interface d'administration

> Plateforme de scraping, de gestion de catalogues et de téléchargements pour **anime-sama.to**.  
> API REST (FastAPI) · Interface admin SPA · CLI complète · Docker ready

![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47a248?logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ed?logo=docker&logoColor=white)

---

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation locale](#installation-locale)
- [Lancement](#lancement)
- [Configuration](#configuration)
- [Docker](#docker)
- [CLI](#cli)
- [API](#api)
- [Sécurité](#sécurité)
- [Groupes et permissions](#groupes-et-permissions)
- [Téléchargements](#téléchargements)
- [OIDC / SSO](#oidc--sso)

---

## Fonctionnalités

| Domaine | Détail |
| --- | --- |
| **Catalogue** | Scraping automatique depuis anime-sama.to, recherche multi-critères (type, langue, genre, état, année), synchronisation épisodes / chapitres |
| **Téléchargements** | Via yt-dlp · progression en temps réel (vitesse, ETA, octets) · annulation instantanée · ZIP multi-épisodes · quotas par utilisateur et par groupe |
| **Planification** | Synchronisations automatiques programmées — recherche par titre dans l'interface, pas besoin de connaître le slug |
| **Utilisateurs** | Rôles `admin` / `user` / `client` · permissions granulaires · blocage temporaire ou permanent |
| **Groupes** | Par catalogue, par genre ou par permission — quotas de sync et de téléchargement configurables |
| **Applications API** | Clients machine-to-machine avec `client_id` / `client_secret` (JWT distinct) |
| **Sécurité** | Middleware IP ban (cache mémoire O(1)) · verrou API total (503 pour tous sauf admins) · bypass admin par JWT |
| **OIDC / SSO** | Google · GitHub · fournisseur personnalisé (discovery URL) |
| **Interface admin** | SPA port 8001 · thème clair / sombre · aucune dépendance JS externe |
| **CLI** | Toutes les opérations admin accessibles en ligne de commande (users, groups, apps, security, dl) |

---

## Architecture

```text
┌─────────────────┐     HTTP      ┌─────────────────────┐
│  Interface      │◄─────────────►│   API FastAPI        │
│  Admin :8001    │               │   main.py  :8000     │
│  admin_main.py  │               │                      │
└─────────────────┘               │  ┌────────────────┐  │
                                  │  │  Middleware     │  │
┌─────────────────┐               │  │  • IP ban       │  │
│  CLI            │  asyncio      │  │  • API lock     │  │
│  cli.py         │◄─────────────►│  │  • CORS         │  │
└─────────────────┘               │  └────────────────┘  │
                                  │                      │
                                  │  ┌────────────────┐  │
                                  │  │  Services       │  │
                                  │  │  • Scraper      │  │
                                  │  │  • Downloader   │  │
                                  │  │  • Scheduler    │  │
                                  │  │  • API Guard    │  │
                                  │  └────────────────┘  │
                                  └──────────┬───────────┘
                                             │ Motor (async)
                                      ┌──────▼───────┐
                                      │   MongoDB     │
                                      │   :27017      │
                                      └──────────────┘
```

**Collections MongoDB :** `catalogues` · `users` · `api_clients` · `groups` · `downloads` · `dl_quotas` · `ip_bans` · `settings` · `schedules` · `sync_history` · `usage`

---

## Prérequis

| Outil | Version |
| --- | --- |
| Python | ≥ 3.12 |
| MongoDB | ≥ 7 |
| ffmpeg | toute version récente (requis par yt-dlp) |
| Playwright Chromium | `playwright install chromium` |

---

## Installation locale

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd anime_sam

# 2. Environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Dépendances Python + navigateur Playwright
pip install -r requirements.txt
playwright install chromium

# 4. Configuration
cp .env.example .env
# Éditez .env — au minimum JWT_SECRET et ADMIN_PASSWORD
```

---

## Lancement

### Script tout-en-un (recommandé)

```bash
python start.py
# ou avec des ports personnalisés :
python start.py --api-port 8000 --admin-port 8001
```

Lance l'API et l'interface admin en parallèle. `Ctrl+C` arrête les deux processus proprement.

### Lancement séparé

```bash
# Terminal 1 — API
python main.py

# Terminal 2 — Interface admin
python admin_main.py
```

**Accès :**

| Service | URL |
| --- | --- |
| API REST | <http://localhost:8000> |
| Documentation (ReDoc — lecture seule) | <http://localhost:8000/docs> |
| Interface admin | <http://localhost:8001> |

---

## Configuration

Copier `.env.example` vers `.env` et adapter les valeurs :

| Variable | Défaut | Description |
| --- | --- | --- |
| `MONGODB_URL` | `mongodb://localhost:27017` | URI de connexion MongoDB |
| `MONGODB_DB` | `anime_sama` | Nom de la base de données |
| `JWT_SECRET` | *(valeur de dev)* | **À changer en production** — clé de signature JWT |
| `JWT_EXPIRE_MINUTES` | `1440` | Durée de vie des tokens (24 h) |
| `ADMIN_USERNAME` | `admin` | Identifiant du compte admin créé au démarrage |
| `ADMIN_PASSWORD` | `admin` | **À changer en production** |
| `API_PORT` | `8000` | Port de l'API |
| `ADMIN_PORT` | `8001` | Port de l'interface admin |
| `BASE_SAMA_URL` | `https://anime-sama.to/` | URL de base du site scrappé |
| `PLAYWRIGHT_PROXY` | *(vide)* | Proxy optionnel pour Playwright (`http://user:pass@host:port`) |
| `OIDC_GOOGLE_CLIENT_ID` | *(vide)* | OAuth2 Google (optionnel) |
| `OIDC_GITHUB_CLIENT_ID` | *(vide)* | OAuth2 GitHub (optionnel) |
| `OIDC_CUSTOM_DISCOVERY_URL` | *(vide)* | SSO personnalisé — discovery URL OIDC |

---

## Docker

### Démarrage rapide

```bash
cp .env.example .env
# Éditez .env

docker compose up -d
```

Cela démarre trois conteneurs : **mongodb**, **api** (:8000) et **admin** (:8001).

```bash
# Suivre les logs
docker compose logs -f api
docker compose logs -f admin

# Arrêter
docker compose down

# Arrêter et supprimer les données
docker compose down -v
```

### Build manuel

```bash
docker build -t anime-sama .

# API seule
docker run -p 8000:8000 --env-file .env \
  -e MONGODB_URL=mongodb://host.docker.internal:27017 \
  anime-sama

# Interface admin seule
docker run -p 8001:8001 --env-file .env \
  -e API_BASE=http://localhost:8000 \
  anime-sama python admin_main.py
```

### Volumes persistants

| Volume | Contenu |
| --- | --- |
| `mongo_data` | Données MongoDB |
| `downloads` | Fichiers téléchargés (ZIP / MP4) |

---

## CLI

La CLI donne accès à toutes les opérations sans passer par l'interface web.  
Elle appelle directement les services Python (pas d'appel HTTP, MongoDB requis).

```bash
python cli.py --help
```

### Catalogue

```bash
python cli.py rechercher "naruto"
python cli.py rechercher "dragon" --type anime --lang vostfr --etat en_cours
python cli.py get dragon-ball                  # récupère ou scrape
python cli.py sync-content dragon-ball         # synchronise épisodes/chapitres
python cli.py saisons naruto
python cli.py films naruto --lang vf
python cli.py episodes naruto saison1 --lang vostfr
python cli.py chapitres naruto 0 --images
python cli.py rafraichir dragon-ball
python cli.py liste
python cli.py update-all
python cli.py planning
```

### Utilisateurs

```bash
python cli.py user liste
python cli.py user get alice
python cli.py user creer alice motdepasse --role user --email alice@example.com
python cli.py user supprimer alice
python cli.py user bloquer alice --raison "Abus" --jusqu-au 2026-12-31
python cli.py user debloquer alice
python cli.py user perms alice --sync --no-delete --no-refresh
python cli.py user quota alice --max 50 --periode month
python cli.py user quota alice --desactiver
python cli.py user groupes alice
```

### Groupes

```bash
python cli.py group liste
python cli.py group creer "Abonnés" --type permission --desc "Accès lecture seule"
python cli.py group get <id>
python cli.py group membres <id>
python cli.py group supprimer <id>
```

### Applications API

```bash
python cli.py app liste
python cli.py app creer "Mon Bot" --desc "Synchronisation automatique"
# → affiche client_id et client_secret (une seule fois)
python cli.py app get cli_xxxxxxxxxxxx
python cli.py app desactiver cli_xxxxxxxxxxxx
python cli.py app activer cli_xxxxxxxxxxxx
python cli.py app regenerer-secret cli_xxxxxxxxxxxx
python cli.py app supprimer cli_xxxxxxxxxxxx
```

### Sécurité

```bash
python cli.py security statut
python cli.py security verrouiller --raison "Maintenance — revenez demain"
python cli.py security deverrouiller
python cli.py security bans
python cli.py security bannir 192.168.1.42 --raison "Scraping abusif"
python cli.py security debannir 192.168.1.42
```

### Téléchargements

```bash
python cli.py dl historique --limit 100
python cli.py dl quotas
python cli.py dl quota-set alice --max-fichiers 10 --max-go 5
python cli.py dl quota-set alice --max-fichiers 10 --max-go 5 --desactiver
python cli.py dl quota-supprimer alice
```

---

## API

Documentation complète (ReDoc, lecture seule) : **<http://localhost:8000/docs>**

### Authentification

```bash
# Utilisateur
POST /auth/login           { "username": "...", "password": "..." }
→ { "access_token": "...", "token_type": "bearer" }

# Application (machine-to-machine)
POST /auth/client-token    { "client_id": "...", "client_secret": "..." }
→ { "access_token": "...", "token_type": "bearer" }
```

Toutes les routes protégées attendent l'en-tête :

```http
Authorization: Bearer <token>
```

### Catalogue

| Méthode | Route | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/catalogues/` | — | Liste résumée |
| `GET` | `/catalogues/rechercher?q=naruto` | — | Recherche multi-critères |
| `GET` | `/catalogues/site/rechercher` | — | Recherche sur anime-sama.to |
| `GET` | `/catalogues/{slug}` | — | Catalogue complet (scrape si absent) |
| `POST` | `/catalogues/{slug}/rafraichir` | user | Force le re-scraping |
| `POST` | `/catalogues/{slug}/sync-content` | user | Synchronise épisodes/chapitres |
| `GET` | `/catalogues/{slug}/sync-content/status` | user | État de la sync en cours |
| `WS` | `/catalogues/{slug}/sync-content/ws` | user | Progression en temps réel (WebSocket) |
| `DELETE` | `/catalogues/{slug}` | user | Supprime de la DB |
| `POST` | `/catalogues/mettre-a-jour-tous` | user | Met à jour tous les EN_COURS |

### Téléchargements

| Méthode | Route | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/download/jobs` | user | Crée un job de téléchargement |
| `GET` | `/download/jobs/{id}` | user | État et progression (vitesse, ETA) |
| `GET` | `/download/jobs/{id}/file` | user | Télécharge le fichier produit |
| `DELETE` | `/download/jobs/{id}` | user | Annule / supprime le job |

### Administration (admin uniquement)

| Méthode | Route | Description |
| --- | --- | --- |
| `GET` | `/admin/api/catalogues` | Catalogue enrichi avec visibilité |
| `PUT` | `/admin/api/catalogues/{slug}` | Modifie les métadonnées |
| `PUT` | `/admin/api/catalogues/{slug}/visibility` | Modifie la visibilité publique |
| `GET/POST` | `/admin/api/clients` | Liste / crée des applications API |
| `PUT/DELETE` | `/admin/api/clients/{cid}` | Modifie / supprime une application |
| `POST` | `/admin/api/clients/{cid}/regenerate-secret` | Nouveau secret |
| `GET/POST` | `/admin/api/groups` | Liste / crée des groupes |
| `PUT/DELETE` | `/admin/api/groups/{gid}` | Modifie / supprime un groupe |
| `POST/DELETE` | `/admin/api/groups/{gid}/members` | Ajoute / retire un membre |
| `GET/POST` | `/admin/api/schedules` | Programmations de sync |
| `GET` | `/admin/api/security/state` | État du verrou API |
| `PUT` | `/admin/api/security/lock` | Verrouille / déverrouille l'API |
| `GET/POST` | `/admin/api/security/ip-bans` | Liste / ajoute un ban IP |
| `DELETE` | `/admin/api/security/ip-bans/{ip}` | Lève un ban IP |
| `GET` | `/admin/api/downloads` | Historique des téléchargements |
| `PUT` | `/admin/api/dl-quotas/{username}` | Configure un quota de téléchargement |

---

## Sécurité

### Ban d'adresses IP

Les IPs bannies sont stockées en MongoDB **et** chargées en mémoire vive au démarrage (cache `set` Python, O(1) par requête). Chaque ban / débannissement met à jour les deux instantanément.

```bash
# Via CLI
python cli.py security bannir 1.2.3.4 --raison "Bot"
python cli.py security debannir 1.2.3.4

# Via API (admin)
POST /admin/api/security/ip-bans  { "ip": "1.2.3.4", "reason": "Bot" }
DELETE /admin/api/security/ip-bans/1.2.3.4
```

### Verrouillage de l'API

Quand l'API est verrouillée :
- **Tous** les utilisateurs et **toutes** les applications reçoivent `503`
- Seuls les comptes avec `role: admin` peuvent passer (via JWT)
- Les routes `/auth/login` et `/admin/api/security/*` restent toujours accessibles

```bash
python cli.py security verrouiller --raison "Maintenance programmée"
python cli.py security deverrouiller
```

### Visibilité des catalogues

Par défaut, tout nouveau catalogue est **privé** (`is_public: false`).  
Un administrateur peut le rendre public depuis l'interface admin ou via l'API :

```bash
PUT /admin/api/catalogues/{slug}/visibility
{ "is_public": true }
```

---

## Groupes et permissions

Les groupes permettent d'accorder des droits à plusieurs utilisateurs à la fois.

### Types de groupes

| Type | Effet |
| --- | --- |
| `catalogue` | Accès à une liste de slugs spécifiques |
| `genre` | Accès à tous les catalogues d'un ou plusieurs genres |
| `permission` | Droits fonctionnels (sync, delete, refresh, download) |

### Permissions configurables par groupe

- `can_sync` / `can_delete` / `can_refresh` / `can_download`
- `download_forbidden_slugs` — slugs interdits au téléchargement
- `download_quota` — limite de fichiers et de Go par jour
- `quota` — limite de synchronisations par période

---

## Téléchargements

Les téléchargements utilisent **yt-dlp** et s'exécutent en arrière-plan.

### Fonctionnement

1. `POST /download/jobs` avec une liste d'épisodes/films
2. Le job passe par les états : `pending → downloading → ready`
3. Progression disponible sur `GET /download/jobs/{id}` (octets, vitesse, ETA)
4. Fichier récupérable sur `GET /download/jobs/{id}/file`
5. Annulation instantanée via `DELETE /download/jobs/{id}`

### Quotas

Deux systèmes de quotas indépendants :

| Système | Portée | Configuration |
| --- | --- | --- |
| **Quota utilisateur** | Par compte | `PUT /admin/api/dl-quotas/{username}` |
| **Quota groupe** | Hérité du groupe | Interface admin → Groupes → Téléchargements |

---

## OIDC / SSO

Activez un ou plusieurs fournisseurs dans `.env` :

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

# URL de callback à déclarer chez le fournisseur
OIDC_CALLBACK_URL=http://localhost:8000/auth/oidc/callback
```

---

## Structure du projet

```text
anime_sam/
├── main.py                   # API FastAPI — port 8000
├── admin_main.py             # Interface admin — port 8001
├── start.py                  # Lancement local (API + admin en parallèle)
├── cli.py                    # CLI complète (Typer + Rich)
├── params.py                 # Variables d'environnement
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── api/
│   ├── routes/
│   │   ├── auth.py           # Login, profil, OIDC, gestion users
│   │   ├── catalogues.py     # Catalogue, sync, recherche, WebSocket
│   │   ├── admin.py          # Clients, planifications, sécurité, historique
│   │   ├── groups.py         # CRUD groupes + membres
│   │   └── download.py       # Jobs de téléchargement + quotas
│   └── dependencies.py       # JWT, EffectiveAccess, vérifications de permissions
│
├── db/
│   ├── connection.py         # Connexion Motor + index MongoDB
│   ├── repository.py         # CRUD catalogues
│   ├── user_repository.py
│   ├── groups_repository.py
│   ├── clients_repository.py
│   ├── downloads_repository.py
│   ├── ip_bans_repository.py # Cache mémoire + persistence MongoDB
│   └── settings_repository.py
│
├── models/                   # Schémas Pydantic (validation entrées/sorties)
│
├── services/
│   ├── catalogue_service.py  # Orchestration scraping + DB
│   ├── downloader.py         # yt-dlp avec annulation et progression
│   ├── scheduler_service.py  # APScheduler — planifications de sync
│   ├── sync_manager.py       # Gestion concurrence des syncs
│   ├── scraper.py            # Playwright — scraping anime-sama.to
│   └── api_guard.py          # Verrou API (cache mémoire + settings DB)
│
└── utils/
    └── logger.py
```

---

## Licence

Usage privé. Projet non officiel, sans affiliation avec anime-sama.to.
