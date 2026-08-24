import { create } from 'zustand'
import axios from 'axios'
import { API_BASE_URL, clearTokens, getToken, getApiError, setRefreshToken, setToken } from '@/api/client'
import { apiClient } from '@/api/client'
import type { User } from '@/api/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  ready: boolean // true une fois la vérification de session initiale terminée
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  ready: false,

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const { data } = await axios.post<{ access_token: string; refresh_token?: string }>(
        `${API_BASE_URL}/auth/login`,
        form,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
      )
      setToken(data.access_token)
      if (data.refresh_token) setRefreshToken(data.refresh_token)

      const { data: me } = await apiClient.get<User>('/auth/me')
      if (me.role !== 'admin') {
        clearTokens()
        throw new Error("Ce compte n'a pas les droits administrateur.")
      }
      set({ user: me, isAuthenticated: true, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw new Error(getApiError(err))
    }
  },

  logout: () => {
    clearTokens()
    set({ user: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    const token = getToken()
    if (!token) {
      set({ ready: true })
      return
    }
    try {
      const { data: me } = await apiClient.get<User>('/auth/me')
      if (me.role !== 'admin') {
        clearTokens()
        set({ user: null, isAuthenticated: false, ready: true })
        return
      }
      set({ user: me, isAuthenticated: true, ready: true })
    } catch {
      clearTokens()
      set({ user: null, isAuthenticated: false, ready: true })
    }
  },
}))
