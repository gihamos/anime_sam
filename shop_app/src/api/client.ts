import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

// Clés localStorage distinctes de celles d'admin_app — shop_app parle à un backend
// entièrement séparé (shop_backend), avec ses propres tokens, jamais interchangeables
// avec ceux de l'API anime_sam.
const TOKEN_KEY = 'anime_sama_shop_token'
const REFRESH_TOKEN_KEY = 'anime_sama_shop_refresh_token'

export const API_BASE_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8010'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

let isRefreshing = false
let refreshQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function processQueue(error: unknown, token: string | null = null) {
  refreshQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)))
  refreshQueue = []
}

function createClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  })

  instance.interceptors.request.use((config) => {
    const token = getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

      if (
        error.response?.status !== 401 ||
        original._retry ||
        original.url?.endsWith('/auth/refresh') ||
        original.url?.endsWith('/auth/login')
      ) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          refreshQueue.push({ resolve, reject })
        }).then((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`
          return instance(original)
        })
      }

      original._retry = true
      isRefreshing = true

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        isRefreshing = false
        clearTokens()
        processQueue(error, null)
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
        )
        setToken(data.access_token)
        if (data.refresh_token) setRefreshToken(data.refresh_token)

        processQueue(null, data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return instance(original)
      } catch (refreshError) {
        const status = (refreshError as AxiosError).response?.status
        if (status === 401 || status === 403) clearTokens()
        processQueue(refreshError, null)
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    },
  )

  return instance
}

export const apiClient = createClient()

/** Message d'erreur lisible à partir d'une erreur axios/API — pour les toasts. */
export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail[0]?.msg ?? 'Erreur inconnue'
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Erreur inconnue'
}
