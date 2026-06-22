import { create } from 'zustand';
import { User } from '@/types';
import { authApi, saveToken, removeToken, getToken } from '@/services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isLoading: false,
  isAuthenticated: false,

  login: async (username, password) => {
    set({ isLoading: true });
    try {
      const tokens = await authApi.login(username, password);
      await saveToken(tokens.access_token);
      const user = await authApi.me();
      set({ user, token: tokens.access_token, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    await removeToken();
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true });
    } catch {
      await removeToken();
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  checkAuth: async () => {
    const token = await getToken();
    if (!token) {
      set({ isAuthenticated: false });
      return false;
    }
    set({ token });
    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true });
      return true;
    } catch {
      await removeToken();
      set({ user: null, token: null, isAuthenticated: false });
      return false;
    }
  },
}));
