import { create } from 'zustand'
import axios from 'axios'
import { API_BASE_URL, clearTokens, getToken, getApiError, setRefreshToken, setToken, apiClient } from '@/api/client'
import type { Customer } from '@/api/types'

interface AuthState {
  customer: Customer | null
  isAuthenticated: boolean
  isLoading: boolean
  ready: boolean
  login: (username: string, password: string) => Promise<Customer>
  register: (username: string, password: string, dateOfBirth: string, email?: string) => Promise<Customer>
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  customer: null,
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

      const { data: me } = await apiClient.get<Customer>('/auth/me')
      set({ customer: me, isAuthenticated: true, isLoading: false })
      return me
    } catch (err) {
      set({ isLoading: false })
      throw new Error(getApiError(err))
    }
  },

  register: async (username, password, dateOfBirth, email) => {
    set({ isLoading: true })
    try {
      await apiClient.post('/auth/register', { username, password, date_of_birth: dateOfBirth, email: email || null })
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
      const { data: me } = await apiClient.get<Customer>('/auth/me')
      set({ customer: me, isAuthenticated: true, isLoading: false })
      return me
    } catch (err) {
      set({ isLoading: false })
      throw new Error(getApiError(err))
    }
  },

  logout: () => {
    clearTokens()
    set({ customer: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    const token = getToken()
    if (!token) {
      set({ ready: true })
      return
    }
    try {
      const { data: me } = await apiClient.get<Customer>('/auth/me')
      set({ customer: me, isAuthenticated: true, ready: true })
    } catch {
      clearTokens()
      set({ customer: null, isAuthenticated: false, ready: true })
    }
  },
}))
