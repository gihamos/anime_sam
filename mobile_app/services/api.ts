import axios, { AxiosInstance, AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';
import {
  Catalogue,
  CatalogueSummary,
  SearchFilters,
  SearchResult,
  AuthTokens,
  User,
  DownloadJob,
  SyncStatus,
} from '@/types';

const TOKEN_KEY = 'anime_sama_token';

export const DEFAULT_API_URL = 'http://localhost:8000';

let apiInstance: AxiosInstance | null = null;

export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  });

  instance.interceptors.request.use(async (config) => {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      if (error.response?.status === 401) {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
      }
      return Promise.reject(error);
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

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

// Auth
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

// Catalogues
export const catalogueApi = {
  list: async (): Promise<CatalogueSummary[]> => {
    const { data } = await getApiClient().get<CatalogueSummary[]>('/catalogues/');
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

  syncContent: async (slug: string): Promise<void> => {
    await getApiClient().post(`/catalogues/${slug}/sync-content`);
  },

  getSyncStatus: async (slug: string): Promise<SyncStatus> => {
    const { data } = await getApiClient().get<SyncStatus>(`/catalogues/${slug}/sync-content/status`);
    return data;
  },

  createSyncWebSocket: (slug: string, baseUrl: string): WebSocket => {
    const wsUrl = baseUrl.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/catalogues/${slug}/sync-content/ws`);
  },
};

// Downloads
export const downloadApi = {
  create: async (params: {
    slug: string;
    saison?: number;
    episodes?: number[];
    films?: string[];
  }): Promise<DownloadJob> => {
    const { data } = await getApiClient().post<DownloadJob>('/api/download/jobs', params);
    return data;
  },

  get: async (jobId: string): Promise<DownloadJob> => {
    const { data } = await getApiClient().get<DownloadJob>(`/api/download/jobs/${jobId}`);
    return data;
  },

  cancel: async (jobId: string): Promise<void> => {
    await getApiClient().delete(`/api/download/jobs/${jobId}`);
  },

  getFileUrl: (jobId: string, baseUrl: string): string => {
    return `${baseUrl}/api/download/jobs/${jobId}/file`;
  },
};

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail[0]?.msg || 'Erreur inconnue';
    return error.message;
  }
  return 'Erreur inconnue';
}
