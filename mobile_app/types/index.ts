export interface Video {
  player: string;
  url: string;
  langue: string;
}

export interface Episode {
  numero: number | string;
  titre?: string;
  videos: Video[];
  thumbnail?: string;
}

export interface Saison {
  numero: number;
  nom?: string;
  episodes: Episode[];
  episodes_synced?: boolean;
}

export interface Film {
  titre: string;
  videos: Video[];
  thumbnail?: string;
  annee?: number;
}

export interface ChapitreScan {
  numero: number | string;
  titre?: string;
  url: string;
  pages?: string[];
}

export interface Scan {
  numero?: number;
  nom?: string;
  chapitres: ChapitreScan[];
}

export interface CatalogueVisibility {
  is_public: boolean;
}

export interface Catalogue {
  slug: string;
  nom: string;
  url?: string;
  image?: string;
  synopsis?: string;
  genres: string[];
  type?: string;
  langue?: string;
  etat?: 'termine' | 'en_cours' | 'abandonne';
  annee?: number;
  note?: number;
  saisons: Saison[];
  films: Film[];
  scans: Scan[];
  episodes_synced?: boolean;
  visibility?: CatalogueVisibility;
}

export interface CatalogueSummary {
  slug: string;
  nom: string;
  image?: string;
  genres: string[];
  type?: string;
  langue?: string;
  etat?: string;
  annee?: number;
  note?: number;
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
  };
  is_blocked?: boolean;
  oidc_provider?: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface DownloadJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  slug: string;
  saison?: number;
  episodes?: number[];
  progress?: number;
  speed?: string;
  eta?: string;
  error?: string;
  created_at: string;
  file_url?: string;
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
