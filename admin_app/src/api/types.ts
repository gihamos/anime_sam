// Types partagés — reflètent les modèles Pydantic du backend (models/user.py,
// models/catalogue.py, models/responses.py). Tenus à jour manuellement, pas de
// génération automatique dans ce projet.

export type Role = 'admin' | 'user'

export interface QuotaConfig {
  enabled: boolean
  period: 'day' | 'month' | 'year'
  max_syncs: number
}

export interface UserPermissions {
  can_sync: boolean
  can_delete: boolean
  can_refresh: boolean
  can_download: boolean
  allowed_catalogues: string[]
  catalogue_content: Record<string, ContentAccess>
  quota: QuotaConfig
  download_forbidden_slugs?: string[]
}

export interface ContentAccess {
  saisons: string[]
  films: string[]
  scans: string[]
}

export interface User {
  username: string
  email: string | null
  role: Role
  is_active: boolean
  is_blocked: boolean
  blocked_reason: string | null
  blocked_until: string | null
  permissions: UserPermissions
  groups: string[]
  oidc_provider: string | null
}

export interface UserCreate {
  username: string
  password: string
  email?: string
  role: Role
  permissions: UserPermissions
}

export interface UserUpdate {
  email?: string
  password?: string
  is_active?: boolean
  is_blocked?: boolean
  blocked_reason?: string | null
  blocked_until?: string | null
  role?: Role
  permissions?: UserPermissions
  groups?: string[]
}

// ─── Catalogues ─────────────────────────────────────────────────────────────

export type TypeContenu = 'anime' | 'scan' | 'film' | 'serie' | 'autre'
export type Etat = 'en_cours' | 'termine' | 'abandonne'
export type Source = 'anime-sama' | 'tmdb-vidzy'

export interface CatalogueVisibility {
  is_public: boolean
  public_saisons: string[]
  public_films: string[]
  public_scans: string[]
}

export interface SaisonSummary {
  slug: string
  nom: string
  lang: string
  total_episodes: number
}

export interface FilmSummary {
  slug: string
  nom: string
  lang: string
}

export interface ScanSummary {
  slug: string
  nom: string
}

export interface CatalogueAdminSummary {
  slug: string
  nom: string
  type_contenu: TypeContenu
  source?: Source
  etat: Etat
  genres: string[]
  langues: string[]
  episodes_synced: boolean
  updated_at: string | null
  created_at: string | null
  visibility: CatalogueVisibility
  saisons: SaisonSummary[]
  films: FilmSummary[]
  scans: ScanSummary[]
}

export interface CatalogueDetail {
  slug: string
  url: string
  nom: string
  titre_alternatif: string | null
  synopsis: string | null
  image: string | null
  genres: string[]
  langues: string[]
  etat: Etat
  type_contenu: TypeContenu
  created_at: string | null
  updated_at: string | null
}

export interface CatalogueUpdate {
  nom?: string
  titre_alternatif?: string
  synopsis?: string
  etat?: Etat
  type_contenu?: TypeContenu
  genres?: string[]
  langues?: string[]
}

export interface Video {
  lecteur: string
  player_url: string | null
}

export interface EpisodeContenu {
  numero: number
  titre: string | null
  videos: Video[]
}

export interface SaisonContenu {
  slug: string
  nom: string
  lang: string
  total_episodes: number
  episodes: EpisodeContenu[]
}

export interface FilmContenu {
  slug: string
  nom: string
  lang: string
  videos: Video[]
}

export interface ChapitreContenu {
  numero: number
  titre: string | null
  images_count: number
}

export interface ScanContenu {
  slug: string
  nom: string
  chapitres: ChapitreContenu[]
}

export interface CatalogueContenu {
  slug: string
  episodes_synced: boolean
  saisons: SaisonContenu[]
  films: FilmContenu[]
  scans: ScanContenu[]
}

export interface SiteSearchResult {
  nom: string
  slug: string
  url: string
  image: string | null
  genres: string[]
}

export interface BulkResult {
  ok: string[]
  errors: Record<string, string>
}

// ─── Films & séries (TMDB) ──────────────────────────────────────────────────

export type TmdbMediaType = 'movie' | 'tv'

export interface TmdbSearchResult {
  tmdb_id: number
  media_type: TmdbMediaType
  slug: string
  nom: string
  image: string | null
  synopsis: string | null
  annee: number | null
  note: number | null
  in_db: boolean
}

// ─── Téléchargements ────────────────────────────────────────────────────────

export interface JobCreated {
  job_id: string
  nb_items: number
  output_name: string
  is_single: boolean
  status: string
}

export interface JobStatus {
  job_id: string
  status: 'pending' | 'downloading' | 'ready' | 'error'
  progress: number
  current: string
  dl_bytes: number
  dl_total: number
  dl_speed: number
  dl_eta: number
  output_name: string
  is_single: boolean
  nb_items: number
  error: string
  ready: boolean
}
