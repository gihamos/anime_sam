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

export interface TmdbGenre {
  id: number
  name: string
}

export interface TmdbGenresResponse {
  movie: TmdbGenre[]
  tv: TmdbGenre[]
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

// ─── Groupes ─────────────────────────────────────────────────────────────────

export type GroupType = 'catalogue' | 'genre' | 'permission'

export interface DownloadQuotaConfig {
  enabled?: boolean
  max_files_per_day?: number
  max_gb_per_day?: number
}

export interface GroupPermissions {
  can_sync: boolean
  can_delete: boolean
  can_refresh: boolean
  can_download: boolean
  download_forbidden_slugs: string[]
  download_quota: DownloadQuotaConfig
  quota: QuotaConfig
}

export interface Group {
  id: string
  name: string
  type: GroupType
  description: string | null
  catalogue_slugs: string[]
  catalogue_content: Record<string, ContentAccess>
  genres: string[]
  permissions: GroupPermissions
  member_count: number
  created_at?: string
  updated_at?: string
}

export interface GroupCreate {
  name: string
  type: GroupType
  description?: string
  catalogue_slugs: string[]
  catalogue_content: Record<string, ContentAccess>
  genres: string[]
  permissions: GroupPermissions
}

export type GroupUpdate = Partial<GroupCreate>

// ─── Applications (clients API) ───────────────────────────────────────────────

export interface ApiClientPermissions {
  can_sync: boolean
  can_delete: boolean
  can_refresh: boolean
  allowed_catalogues: string[]
  catalogue_content: Record<string, ContentAccess>
  quota: QuotaConfig
}

export interface ApiClient {
  client_id: string
  name: string
  description: string | null
  is_active: boolean
  permissions: ApiClientPermissions
  created_at?: string
  updated_at?: string
}

export interface ApiClientCreated extends ApiClient {
  client_secret: string
}

export interface SecretRegenerated {
  client_id: string
  client_secret: string
}

// ─── Planification ─────────────────────────────────────────────────────────

export type ScheduleFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'custom'

export interface Schedule {
  id: string
  slug: string
  frequency: ScheduleFrequency
  hour: number
  minute: number
  day_of_week: number | null
  day_of_month: number | null
  interval_days: number | null
  description: string | null
  active: boolean
  last_run: string | null
  next_run: string | null
  created_at?: string
  updated_at?: string
}

export interface ScheduleCreate {
  slug: string
  frequency: ScheduleFrequency
  hour: number
  minute: number
  day_of_week?: number | null
  day_of_month?: number | null
  interval_days?: number | null
  description?: string | null
  active: boolean
}

export type ScheduleUpdate = Partial<Omit<ScheduleCreate, 'slug'>>

export interface PlanningAnime {
  titre: string
  slug: string
  url: string
  url_saison: string
  image: string | null
  heure: string
  saison_info: string
  lang: string
}

export interface PlanningJour {
  jour: string
  date: string
  animes: PlanningAnime[]
}

export interface SyncHistoryEntry {
  slug: string
  triggered_by: string
  started_at: string
  ended_at: string
  duration_s: number
  status: 'completed' | 'cancelled' | 'error'
  total_items: number
}

// ─── Téléchargements (admin) ──────────────────────────────────────────────────

export interface DownloadRecord {
  username: string
  slug: string
  type: string | null
  nb_files: number
  details: string
  size_bytes: number
  date: string
}

export interface DlQuota {
  username: string
  max_files_per_day: number
  max_gb_per_day: number
  can_download: boolean
}

// ─── Sécurité ───────────────────────────────────────────────────────────────

export interface SecurityState {
  locked: boolean
  reason: string
  banned_count: number
}

export interface IpBan {
  ip: string
  reason: string
  banned_at: string | null
  banned_by: string
}

// ─── Connexions (access logs) ─────────────────────────────────────────────────

export interface AccessLogEntry {
  ip: string
  username: string | null
  method: string
  path: string
  status_code: number
  user_agent: string
  timestamp: string
}

export interface AccessStats {
  total: number
  unique_ips: number
  auth_count: number
  anon_count: number
  top_users: { username: string; count: number }[]
  top_ips: { ip: string; count: number }[]
  hourly_24h: { hour: string; count: number }[]
}
