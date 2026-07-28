// ─── Vidéo / épisode ─────────────────────────────────────────────────────────

export interface Video {
  lecteur: string;    // nom du lecteur (sendvid, gogo, etc.)
  player_url: string; // URL de l'iframe embed
}

// Réponse de GET /catalogues/{slug}/saisons/{saison_slug}/episodes
// { "1": [Video, …], "2": [Video, …] }
export type EpisodesResponse = Record<string, Video[]>;

// Un épisode déjà synchronisé en DB (présent directement dans SaisonMeta.episodes)
export interface Episode {
  numero: number;
  titre?: string;
  videos: Video[];
}

// Réponse de GET /api/stream/resolve — URL embed résolue en flux direct
export interface ResolvedStream {
  url:        string | null;
  // Chemin relatif vers /api/stream/proxy — headers déjà injectés côté serveur.
  // À préférer : fonctionne avec n'importe quel lecteur (interne ou externe),
  // y compris pour les segments HLS individuels (le manifest est réécrit).
  proxy_url:  string | null;
  audio_url:  string | null;
  ext:        string;
  protocol:   string;
  headers:    Record<string, string>;
  title:      string;
  duration:   number | null;
  merged:     boolean; // true si vidéo et audio sont sur des URLs séparées
}

// ─── Métadonnées de catalogue ─────────────────────────────────────────────────

// Saison telle que renvoyée par GET /catalogues/{slug}
export interface SaisonMeta {
  slug: string;
  nom: string;
  lang: string;
  total_episodes: number;
  // Présent (non vide) si les épisodes ont déjà été synchronisés en DB —
  // dans ce cas pas besoin de rescraper via /saisons/{slug}/episodes (lent).
  episodes?: Episode[];
}

// Film tel que renvoyé par GET /catalogues/{slug}
export interface FilmMeta {
  slug: string;
  nom: string;
  lang: string;
  // Idem SaisonMeta.episodes : présent si déjà synchronisé en DB.
  videos?: Video[];
}

// ─── Scans / manga ───────────────────────────────────────────────────────────

export interface LecteurScan {
  lecteur: string;
  player_url: string | null;
}

export interface ChapitreScan {
  numero: number;
  titre: string | null;
  url: string;
  lecteurs: LecteurScan[];
  images: string[];     // URLs des pages (vides si non scrapées)
}

export interface ScanMeta {
  nom: string;
  slug: string;
  lang: string | null;
  url: string;
  image: string | null;
  chapitres: ChapitreScan[];
}

export interface Catalogue {
  slug: string;
  nom: string;
  image?: string;
  synopsis?: string;
  genres: string[];
  langues?: string[];
  type_contenu?: string;
  etat?: string;
  saisons: SaisonMeta[];
  films: FilmMeta[];
  scans: ScanMeta[];
  episodes_synced?: boolean;
  titre_alternatif?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CatalogueSummary {
  slug: string;
  nom: string;
  image?: string;
  genres: string[];
  // type_contenu vient de /mycatalogues/ ; type vient des endpoints favoris/reco
  type_contenu?: string;
  type?: string;
  langue?: string;
  langues?: string[];
  etat?: string;
  annee?: number;
  note?: number;
  updated_at?: string;
  created_at?: string;
  // Présents sur /mycatalogues/ et /catalogues/rechercher (métadonnées légères,
  // sans les listes lourdes d'épisodes/vidéos/chapitres) — permet de savoir si
  // un catalogue contient réellement des scans/films, indépendamment de son
  // type_contenu principal (un catalogue "anime" peut avoir des scans attachés).
  saisons?: SaisonMeta[];
  films?:   FilmMeta[];
  scans?:   ScanMeta[];
}

export interface SearchFilters {
  q?: string;
  type?: string;
  langue?: string;
  genre?: string;
  etat?: string;
  annee?: number;
  page?: number;
  limit?: number;
}

export interface SearchResult {
  results: CatalogueSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface User {
  username: string;
  email?: string;
  role: 'admin' | 'user';
  permissions: {
    can_sync: boolean;
    can_delete: boolean;
    can_refresh: boolean;
    can_download: boolean;
    allowed_catalogues: string[];
  };
  is_blocked?: boolean;
  oidc_provider?: string;
}

// ─── Favoris ─────────────────────────────────────────────────────────────────

// Élément d'un favori (shape retourné par GET /auth/me/favoris)
export interface FavorisItem {
  slug:    string;
  nom:     string;
  image?:  string;
  genres:  string[];
  type?:   string;   // type_contenu normalisé
  etat?:   string;
  langues: string[];
  annee?:  number;
  note?:   number;
}

// Réponse GET /auth/me/favoris
export interface FavorisResponse {
  slugs:      string[];
  catalogues: FavorisItem[];
}

// ─── Recommandations ──────────────────────────────────────────────────────────

// Élément retourné par GET /auth/me/recommendations
export interface RecommendationItem {
  slug:   string;
  nom:    string;
  image?: string;
  genres: string[];
  type?:  string;
  langue?: string;
  etat?:  string;
  annee?: number;
  note?:  number;
  score:  number;  // 0.0 = cold start ; plus élevé = plus pertinent
}

// Alias utilisé dans les composants (rétrocompatibilité)
export type Recommendation = RecommendationItem;

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
}

// Réponse POST /api/download/jobs
export interface JobCreated {
  job_id: string;
  nb_items: number;
  output_name: string;
  is_single: boolean;
  status: string;
}

// Réponse GET /api/download/jobs/{id}
export interface JobStatus {
  job_id: string;
  status: 'pending' | 'downloading' | 'ready' | 'error';
  progress: number;
  current: string;
  dl_bytes: number;
  dl_total: number;
  dl_speed: number;
  dl_eta: number;
  output_name: string;
  is_single: boolean;
  nb_items: number;
  error: string;
  ready: boolean;
}

// Job suivi côté client (enrichi)
export interface ActiveJob {
  job_id: string;
  slug: string;
  catalogue_nom: string;
  label: string;           // "Naruto - Saison 1 - Episode 01"
  status: 'pending' | 'downloading' | 'ready' | 'error';
  progress: number;
  dl_speed: number;
  dl_eta: number;
  output_name: string;
  is_single: boolean;
  nb_items: number;
  error: string;
  created_at: number;      // timestamp ms
  job_type?: 'video' | 'scan';
  // Contexte scan (présent si job_type === 'scan')
  scan_slug?: string;
  chapitre_nums?: number[];
}

// ─── Scan téléchargement ──────────────────────────────────────────────────────

export interface ScanJobCreated {
  job_id: string;
  slug: string;
  scan_slug: string;
  chapters: Array<{ num: number; titre: string | null; page_count: number }>;
  total_pages: number;
  status: string;
}

export interface ScanJobStatus {
  job_id: string;
  status: 'pending' | 'downloading' | 'ready' | 'error';
  progress: number;
  total_pages: number;
  done_pages: number;
  error: string;
  ready: boolean;
}

export interface ScanJobManifest {
  job_id: string;
  slug: string;
  scan_slug: string;
  chapters: Array<{ num: number; titre: string | null; page_count: number }>;
}

// Chapitre scan stocké localement sur l'appareil
export interface LocalScanChapter {
  id: string;              // "{slug}_{scan_slug}_{num}"
  slug: string;
  catalogue_nom: string;
  scan_slug: string;
  scan_nom: string;
  chapitre_num: number;
  chapitre_titre: string | null;
  local_pages: string[];   // URIs expo-file-system (file://…)
  page_count: number;
  size_bytes: number;
  downloaded_at: number;   // timestamp ms
}

// Fichier téléchargé et enregistré localement sur l'appareil
export interface LocalFile {
  id: string;
  slug: string;
  catalogue_nom: string;
  label: string;
  output_name: string;
  local_uri: string;       // chemin expo-file-system
  is_single: boolean;      // mp4 ou zip
  size_bytes: number;
  downloaded_at: number;   // timestamp ms
}

export interface SyncStatus {
  slug: string;
  status: 'idle' | 'syncing' | 'done' | 'error' | 'never_synced';
  progress: number;      // 0-100
  message?: string;
  started_at?: string;
}

export type ContentType = 'anime' | 'film' | 'scan';
export type AnimeState = 'termine' | 'en_cours' | 'abandonne';
export type Language = 'vf' | 'vostfr' | 'vo';
