// ─── Vidéo / épisode ─────────────────────────────────────────────────────────

export interface Video {
  lecteur: string;    // nom du lecteur (sendvid, gogo, etc.)
  player_url: string; // URL de l'iframe embed
}

// Réponse de GET /catalogues/{slug}/saisons/{saison_slug}/episodes
// { "1": [Video, …], "2": [Video, …] }
export type EpisodesResponse = Record<string, Video[]>;

// ─── Métadonnées de catalogue ─────────────────────────────────────────────────

// Saison telle que renvoyée par GET /catalogues/{slug}
export interface SaisonMeta {
  slug: string;
  nom: string;
  lang: string;
  total_episodes: number;
}

// Film tel que renvoyé par GET /catalogues/{slug}
export interface FilmMeta {
  slug: string;
  nom: string;
  lang: string;
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
  running: boolean;
  progress?: number;
  message?: string;
  error?: string;
}

export type ContentType = 'anime' | 'film' | 'scan';
export type AnimeState = 'termine' | 'en_cours' | 'abandonne';
export type Language = 'vf' | 'vostfr' | 'vo';
