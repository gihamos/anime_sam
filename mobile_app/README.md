# Anime Sama — Application Mobile

Client mobile non officiel pour l'API Anime Sama. Parcourez, lisez et téléchargez animés, films et scans directement depuis votre téléphone, avec support hors ligne.

![React Native](https://img.shields.io/badge/React_Native-0.81-61dafb?logo=react&logoColor=white)
![Expo](https://img.shields.io/badge/Expo-54-000020?logo=expo)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178c6?logo=typescript&logoColor=white)

## Ce que ça fait

- Navigation du catalogue par sections (en cours, films, scans) et recherche avancée
- Lecteur vidéo intégré avec sélection du lecteur, plein écran et verrouillage d'orientation
- Lecteur scan avec défilement vertical, navigation entre chapitres
- Téléchargements vidéo et scan en arrière-plan — lecture hors ligne sans réseau
- Cache local des catalogues (TTL 1 h) pour des chargements instantanés au retour
- Authentification JWT avec refresh automatique, OIDC (Google, GitHub, SSO custom)
- Section admin pour les comptes admin : historique des connexions, statistiques, ban IP

## Prérequis

Node.js ≥ 18, npm ≥ 9, et l'app **Expo Go** sur votre téléphone pour le développement.

Un serveur Anime Sama API accessible depuis le téléphone est requis.

## Installation et lancement

```bash
cd mobile_app
npm install
npm start        # génère un QR code à scanner avec Expo Go
```

## Configuration de l'API

Au premier démarrage, l'application affiche un écran de configuration. Saisissez l'adresse de votre serveur (`http://192.168.1.x:8000`), testez la connexion, puis sauvegardez. L'URL est stockée de façon sécurisée sur l'appareil et peut être modifiée à tout moment via **Profil → Configuration API**.

## Structure

```text
mobile_app/
├── app/
│   ├── _layout.tsx             # Root : QueryClient, guards, job poller
│   ├── setup.tsx               # Onboarding — config URL + test connexion
│   ├── (tabs)/
│   │   ├── index.tsx           # Accueil
│   │   ├── search.tsx          # Recherche
│   │   ├── downloads.tsx       # Téléchargements en cours / hors ligne
│   │   ├── favoris.tsx
│   │   └── profile.tsx         # Profil, config API, admin
│   ├── anime/[slug].tsx        # Fiche catalogue
│   ├── player/                 # Lecteur vidéo
│   ├── scan-reader/            # Lecteur scan
│   └── admin/connections.tsx   # Connexions & gestion IP (admin)
│
├── services/
│   ├── api.ts                  # Client Axios avec interceptors JWT
│   └── catalogueCache.ts       # Cache FileSystem par slug
│
├── stores/                     # Zustand — auth, settings, downloads, player, scan
├── hooks/                      # React Query — catalogue, téléchargements, favoris
├── constants/colors.ts         # Design tokens
└── types/index.ts
```

Le cache catalogue fonctionne en stale-while-revalidate : les données sont injectées depuis le disque dans React Query avant que le réseau réponde, ce qui évite tout écran vide au chargement. En dessous du TTL d'une heure, aucune requête réseau n'est envoyée.

## Stack

React Native 0.81, Expo 54, Expo Router, TypeScript, TanStack React Query 5, Zustand 5, Axios, expo-secure-store, expo-file-system, react-native-video, @shopify/flash-list.

## Build APK

```bash
npm install -g eas-cli
eas login
eas build --platform android --profile preview
```

Le build se fait sur les serveurs Expo (~10-20 min). Un lien de téléchargement direct est fourni à la fin.

---

Développé par **Taïse De Thèse Yabie** — [github.com/gihamos](https://github.com/gihamos/)

> Projet non officiel, sans affiliation avec anime-sama.to.
