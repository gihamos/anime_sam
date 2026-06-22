import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';
import {
  Catalogue,
  CatalogueSummary,
  SearchFilters,
  SearchResult,
  AuthTokens,
  User,
  JobCreated,
  JobStatus,
  ScanJobCreated,
  ScanJobStatus,
  ScanJobManifest,
  SyncStatus,
  EpisodesResponse,
  FavorisResponse,
  RecommendationItem,
} from '@/types';

const TOKEN_KEY         = 'anime_sama_token';
const REFRESH_TOKEN_KEY = 'anime_sama_refresh_token';

export const DEFAULT_API_URL = 'http://localhost:8000';

let apiInstance: AxiosInstance | null = null;

// Évite plusieurs appels simultanés à /auth/refresh
let isRefreshing = false;
let refreshQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null = null) {
  refreshQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  refreshQueue = [];
}

export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  });

  // Injecte le token d'accès sur chaque requête
  instance.interceptors.request.use(async (config) => {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Sur 401 : tente un refresh transparent avant de rejeter
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

      // Ne pas retenter si ce n'est pas un 401, ou si on boucle déjà
      if (
        error.response?.status !== 401 ||
        original._retry ||
        original.url?.endsWith('/auth/refresh')
      ) {
        return Promise.reject(error);
      }

      // Si un refresh est déjà en cours, mettre la requête en file d'attente
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          refreshQueue.push({ resolve, reject });
        }).then((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`;
          return instance(original);
        });
      }

      original._retry = true;
      isRefreshing = true;

      const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      if (!refreshToken) {
        isRefreshing = false;
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        processQueue(error, null);
        return Promise.reject(error);
      }

      try {
        // Appel direct (sans passer par l'instance) pour éviter toute récursion
        const { data } = await axios.post<AuthTokens>(`${baseURL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        await SecureStore.setItemAsync(TOKEN_KEY, data.access_token);
        if (data.refresh_token) {
          await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.refresh_token);
        }

        processQueue(null, data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return instance(original);
      } catch (refreshError) {
        // Ne vider les tokens que si le serveur rejette explicitement le refresh (401/403).
        // Une erreur réseau (serveur indisponible) ne doit pas déconnecter l'utilisateur.
        const httpStatus = (refreshError as AxiosError).response?.status;
        if (httpStatus === 401 || httpStatus === 403) {
          await SecureStore.deleteItemAsync(TOKEN_KEY);
          await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
        }
        processQueue(refreshError, null);
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
  );

  return instance;
}

export function getApiClient(): AxiosInstance {
  if (!apiInstance) {
    apiInstance = createApiClient(DEFAULT_API_URL);
  }
  return apiInstance;
}

export function setApiBaseUrl(url: string): void {
  apiInstance = createApiClient(url);
}

// ─── SecureStore helpers ──────────────────────────────────────────────────────

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function saveRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function removeRefreshToken(): Promise<void> {
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (username: string, password: string): Promise<AuthTokens> => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const { data } = await getApiClient().post<AuthTokens>('/auth/login', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return data;
  },

  me: async (): Promise<User> => {
    const { data } = await getApiClient().get<User>('/auth/me');
    return data;
  },
};

// ─── Favoris ──────────────────────────────────────────────────────────────────

export const favorisApi = {
  get: async (): Promise<FavorisResponse> => {
    const { data } = await getApiClient().get<FavorisResponse>('/auth/me/favoris');
    return data;
  },

  add: async (slug: string): Promise<void> => {
    await getApiClient().post(`/auth/me/favoris/${slug}`);
  },

  remove: async (slug: string): Promise<void> => {
    await getApiClient().delete(`/auth/me/favoris/${slug}`);
  },

  recommendations: async (): Promise<RecommendationItem[]> => {
    const { data } = await getApiClient().get<RecommendationItem[]>('/auth/me/recommendations');
    return data;
  },
};

// ─── Catalogues ───────────────────────────────────────────────────────────────

export const catalogueApi = {
  list: async (): Promise<CatalogueSummary[]> => {
    const { data } = await getApiClient().get<CatalogueSummary[]>('/mycatalogues/');
    return data;
  },

  search: async (filters: SearchFilters): Promise<SearchResult> => {
    const { data } = await getApiClient().get<SearchResult>('/catalogues/rechercher', {
      params: filters,
    });
    return data;
  },

  searchSite: async (q: string): Promise<CatalogueSummary[]> => {
    const { data } = await getApiClient().get<CatalogueSummary[]>('/catalogues/site/rechercher', {
      params: { q },
    });
    return data;
  },

  get: async (slug: string): Promise<Catalogue> => {
    const { data } = await getApiClient().get<Catalogue>(`/catalogues/${slug}`);
    return data;
  },

  refresh: async (slug: string): Promise<void> => {
    await getApiClient().post(`/catalogues/${slug}/rafraichir`);
  },

  getEpisodes: async (slug: string, saisonSlug: string, lang: string): Promise<EpisodesResponse> => {
    const { data } = await getApiClient().get<EpisodesResponse>(
      `/catalogues/${slug}/saisons/${saisonSlug}/episodes`,
      { params: { lang } }
    );
    return data;
  },

  syncContent: async (slug: string): Promise<void> => {
    await getApiClient().post(`/catalogues/${slug}/sync-content`);
  },

  getSyncStatus: async (slug: string): Promise<SyncStatus> => {
    const { data } = await getApiClient().get<SyncStatus>(`/catalogues/${slug}/sync-content/status`);
    return data;
  },

  createSyncWebSocket: (slug: string, baseUrl: string): WebSocket => {
    const wsUrl = baseUrl.replace(/^http/, 'ws');
    return new WebSocket(`${wsUrl}/catalogues/${slug}/sync-content/ws`);
  },
};

// ─── Téléchargements ─────────────────────────────────────────────────────────

export const downloadApi = {
  createEpisodeJob: async (params: {
    slug: string;
    saison_idx: number;
    nums?: number[];
  }): Promise<JobCreated> => {
    const { data } = await getApiClient().post<JobCreated>('/api/download/jobs', params);
    return data;
  },

  createFilmJob: async (params: {
    slug: string;
    film_idx: number;
  }): Promise<JobCreated> => {
    const { data } = await getApiClient().post<JobCreated>('/api/download/jobs', params);
    return data;
  },

  getStatus: async (jobId: string): Promise<JobStatus> => {
    const { data } = await getApiClient().get<JobStatus>(`/api/download/jobs/${jobId}`);
    return data;
  },

  cancel: async (jobId: string): Promise<void> => {
    await getApiClient().delete(`/api/download/jobs/${jobId}`);
  },

  getFileUrl: (jobId: string, baseUrl: string, token: string | null): string => {
    const t = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${baseUrl}/api/download/jobs/${jobId}/file${t}`;
  },
};

// ─── Téléchargements scans ────────────────────────────────────────────────────

export const scanDownloadApi = {
  createJob: async (params: {
    slug: string;
    scan_slug: string;
    chapitre_nums: number[];
  }): Promise<ScanJobCreated> => {
    const { data } = await getApiClient().post<ScanJobCreated>('/api/download/scan/jobs', params);
    return data;
  },

  getStatus: async (jobId: string): Promise<ScanJobStatus> => {
    const { data } = await getApiClient().get<ScanJobStatus>(`/api/download/scan/jobs/${jobId}`);
    return data;
  },

  getManifest: async (jobId: string): Promise<ScanJobManifest> => {
    const { data } = await getApiClient().get<ScanJobManifest>(`/api/download/scan/jobs/${jobId}/manifest`);
    return data;
  },

  getPageUrl: (jobId: string, c: number, p: number, baseUrl: string, token: string | null): string => {
    const t = token ? `&token=${encodeURIComponent(token)}` : '';
    return `${baseUrl}/api/download/scan/jobs/${jobId}/page?c=${c}&p=${p}${t}`;
  },

  cancel: async (jobId: string): Promise<void> => {
    await getApiClient().delete(`/api/download/scan/jobs/${jobId}`);
  },
};

// ─── Admin : logs de connexion ───────────────────────────────────────────────

export interface AccessLog {
  ip:          string;
  username:    string | null;
  method:      string;
  path:        string;
  status_code: number;
  user_agent:  string;
  timestamp:   string;
}

export interface AccessStats {
  total:      number;
  unique_ips: number;
  auth_count: number;
  anon_count: number;
  top_users:  { username: string; count: number }[];
  top_ips:    { ip: string;       count: number }[];
  hourly_24h: { hour: string;     count: number }[];
}

export const adminLogsApi = {
  getLogs: async (params?: {
    ip?:        string;
    username?:  string;
    auth_only?: boolean;
    anon_only?: boolean;
    date_from?: string;
    date_to?:   string;
    limit?:     number;
  }): Promise<AccessLog[]> => {
    const { data } = await getApiClient().get<AccessLog[]>('/admin/api/access-logs', { params });
    return data;
  },

  getStats: async (): Promise<AccessStats> => {
    const { data } = await getApiClient().get<AccessStats>('/admin/api/access-logs/stats');
    return data;
  },

  clearLogs: async (): Promise<{ deleted: number }> => {
    const { data } = await getApiClient().delete<{ deleted: number }>('/admin/api/access-logs');
    return data;
  },

  banIp: async (ip: string, reason?: string): Promise<void> => {
    await getApiClient().post('/admin/api/security/ip-bans', { ip, reason: reason ?? '' });
  },

  unbanIp: async (ip: string): Promise<void> => {
    await getApiClient().delete(`/admin/api/security/ip-bans/${ip}`);
  },

  getBannedIps: async (): Promise<{ ip: string; reason: string; banned_by: string; created_at: string }[]> => {
    const { data } = await getApiClient().get('/admin/api/security/ip-bans');
    return data;
  },
};

// ─── Test de connexion ────────────────────────────────────────────────────────

export async function testApiConnection(
  url: string,
): Promise<{ ok: boolean; message: string }> {
  const clean = url.trim().replace(/\/$/, '');
  try {
    const res = await axios.get<{ message?: string }>(`${clean}/`, { timeout: 6000 });
    if (res.status === 200 && res.data?.message) {
      return { ok: true, message: res.data.message };
    }
    return { ok: false, message: `Réponse inattendue (HTTP ${res.status})` };
  } catch (err) {
    if (axios.isAxiosError(err)) {
      if (!err.response) {
        return { ok: false, message: 'Serveur inaccessible — vérifiez l\'adresse et le réseau' };
      }
      return { ok: false, message: `Erreur HTTP ${err.response.status}` };
    }
    return { ok: false, message: 'Erreur inconnue' };
  }
}

// ─── Utilitaire erreur ────────────────────────────────────────────────────────

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail[0]?.msg || 'Erreur inconnue';
    return error.message;
  }
  return 'Erreur inconnue';
}
