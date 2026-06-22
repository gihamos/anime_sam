# Anime Sama — Application Mobile

> Client mobile officiel de l'API Anime Sama.  
> Parcourez, lisez et téléchargez votre catalogue d'animés, films et scans — même hors ligne.

![React Native](https://img.shields.io/badge/React_Native-0.81-61dafb?logo=react&logoColor=white)
![Expo](https://img.shields.io/badge/Expo-54-000020?logo=expo)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178c6?logo=typescript&logoColor=white)

---

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Écrans](#écrans)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Lancement](#lancement)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Développeur](#développeur)

---

## Fonctionnalités

| Domaine | Détail |
| --- | --- |
| **Catalogue** | Navigation par sections (en cours, films, scans), recherche avancée multi-critères |
| **Lecteur vidéo** | Lecture intégrée avec sélection du lecteur, mode plein écran, verrouillage d'orientation |
| **Lecteur scan** | Défilement vertical page par page, navigation entre chapitres |
| **Téléchargements vidéo** | Téléchargement en arrière-plan, progression en temps réel (vitesse, ETA), lecture hors ligne |
| **Téléchargements scan** | Téléchargement de chapitres complets, lecture hors ligne sans réseau |
| **Cache catalogue** | Cache JSON par catalogue (TTL 1 h), chargement instantané, synchronisation manuelle |
| **Favoris** | Ajout / retrait en un tap, liste persistante |
| **Authentification** | Login JWT, rafraîchissement automatique du token, OIDC (Google / GitHub / SSO personnalisé) |
| **Onboarding** | Configuration guidée de l'URL du serveur avec test de connexion avant démarrage |
| **Admin mobile** | Historique des connexions, statistiques d'usage, ban IP en un tap (rôle admin uniquement) |

---

## Écrans

```text
app/
├── setup.tsx                  # Onboarding — configuration URL API + test connexion
├── (tabs)/
│   ├── index.tsx              # Accueil — sections par catégorie avec navigation filtrée
│   ├── search.tsx             # Recherche avancée (type, état, filtre depuis l'accueil)
│   ├── downloads.tsx          # Téléchargements en cours · Vidéos · Scans hors ligne
│   ├── favoris.tsx            # Liste des favoris
│   └── profile.tsx            # Profil utilisateur, config API, section admin
├── anime/[slug].tsx           # Fiche catalogue — saisons, films, scans, téléchargements
├── player/index.tsx           # Lecteur vidéo plein écran
├── scan-reader/index.tsx      # Lecteur manga/scan (online + offline)
└── admin/
    └── connections.tsx        # Historique connexions & gestion IP (admin)
```

---

## Prérequis

| Outil | Version |
| --- | --- |
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Expo Go | Application sur iOS / Android (développement) |

> Un serveur **Anime Sama API** actif et accessible depuis le téléphone est obligatoire.

---

## Installation

```bash
# Aller dans le dossier mobile
cd mobile_app

# Installer les dépendances
npm install
```

---

## Configuration

L'application fonctionne avec n'importe quelle instance de l'API Anime Sama.  
L'URL du serveur se configure directement dans l'application.

### Premier lancement — Onboarding

Au premier démarrage, l'écran de configuration s'affiche automatiquement :

1. Saisir l'adresse du serveur — ex : `http://192.168.1.48:8000`
2. Appuyer sur **Tester la connexion** pour vérifier l'accessibilité
3. Si le test réussit, appuyer sur **Sauvegarder et démarrer**

> L'adresse est sauvegardée de façon sécurisée sur l'appareil via `expo-secure-store`.

### Modifier l'URL ultérieurement

**Profil → Configuration API** — même interface test + sauvegarde, accessible à tout moment.

---

## Lancement

```bash
# Démarrer Expo (QR code pour Expo Go)
npm start

# Ou cibler directement une plateforme
npm run android
npm run ios
```

Scannez le QR code avec **Expo Go** (Android) ou l'app **Appareil photo** (iOS).

---

## Architecture

```text
mobile_app/
│
├── app/                        # Expo Router — pages et layouts
│   ├── _layout.tsx             # Root layout : QueryClient, guards, job poller global
│   ├── setup.tsx               # Onboarding
│   ├── (tabs)/                 # Navigation par onglets
│   ├── anime/[slug].tsx        # Fiche catalogue dynamique
│   ├── player/                 # Lecteur vidéo
│   ├── scan-reader/            # Lecteur scan
│   └── admin/                  # Écrans administration
│
├── services/
│   ├── api.ts                  # Client Axios : auth, catalogue, téléchargements, admin
│   └── catalogueCache.ts       # Cache FileSystem JSON par slug (TTL 1 h)
│
├── stores/                     # État global Zustand
│   ├── authStore.ts            # Session JWT, refresh automatique du token
│   ├── settingsStore.ts        # URL API, flag ready pour onboarding
│   ├── downloadStore.ts        # Fichiers locaux téléchargés (vidéos + scans)
│   ├── playerStore.ts          # État lecteur vidéo
│   └── scanReaderStore.ts      # État lecteur scan (chapitre, index, mode offline)
│
├── hooks/
│   ├── useAnime.ts             # React Query : catalogue, sync, favoris
│   ├── useDownloads.ts         # Job polling, démarrage téléchargements
│   └── useFavorites.ts         # Gestion favoris
│
├── components/
│   └── ui/                     # Composants réutilisables
│
├── constants/
│   └── colors.ts               # Palette, espacements, typographie, rayons
│
└── types/
    └── index.ts                # Types TypeScript globaux
```

### Flux de données

```text
Composant React
    │
    ├── useQuery (React Query)
    │       │
    │       ├── [cache chaud]   → données servies immédiatement
    │       ├── [cache disque]  → FileSystem JSON injecté via setQueryData
    │       └── [réseau]        → api.ts → Axios → Anime Sama API
    │
    └── Zustand store           → état local persistant (SecureStore / mémoire)
```

### Stratégie cache catalogue

| Situation | Comportement |
| --- | --- |
| Cache < 1 h | Données servies sans appel réseau |
| Cache ≥ 1 h | Affichage immédiat + refetch en arrière-plan |
| Pas de cache | Chargement réseau classique |
| Bouton sync | Invalide le cache et force le rechargement |

---

## Technologies

| Bibliothèque | Usage |
| --- | --- |
| **Expo 54 / Expo Router** | Navigation fichier-based, gestion des écrans |
| **React Native 0.81** | Framework mobile cross-platform |
| **TypeScript 5.3** | Typage statique |
| **TanStack React Query 5** | Cache serveur, stale-while-revalidate |
| **Zustand 5** | État global léger |
| **Axios** | Client HTTP avec interceptors JWT automatiques |
| **expo-secure-store** | Stockage sécurisé du token et de l'URL API |
| **expo-file-system** | Cache local des catalogues et fichiers scans |
| **react-native-video** | Lecteur vidéo natif |
| **react-native-gesture-handler / reanimated** | Animations et gestes fluides |
| **@shopify/flash-list** | Listes hautes performances |

---

## Développeur

Développé par **Taïse De Thèse Yabie**  
GitHub : [https://github.com/gihamos/](https://github.com/gihamos/)

> Application non officielle — aucune affiliation avec anime-sama.to.
