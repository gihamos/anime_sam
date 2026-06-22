import { create } from 'zustand';
import { User } from '@/types';
import {
  authApi,
  saveToken, removeToken, getToken,
  saveRefreshToken, removeRefreshToken,
} from '@/services/api';

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

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  isAuthenticated: false,

  login: async (username, password) => {
    set({ isLoading: true });
    try {
      const tokens = await authApi.login(username, password);
      await saveToken(tokens.access_token);
      if (tokens.refresh_token) {
        await saveRefreshToken(tokens.refresh_token);
      }
      const user = await authApi.me();
      set({ user, token: tokens.access_token, isAuthenticated: true });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    await removeToken();
    await removeRefreshToken();
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true });
    } catch {
      await removeToken();
      await removeRefreshToken();
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  checkAuth: async () => {
    const token = await getToken();

    if (!token) {
      // Pas de token stocké — l'intercepteur ne pourra pas rafraîchir non plus
      set({ isAuthenticated: false });
      return false;
    }

    set({ token });

    try {
      // Si le token d'accès est expiré, l'intercepteur 401 tente automatiquement
      // le refresh puis rejoue la requête — transparent pour ce code.
      const user = await authApi.me();
      // Récupérer le token potentiellement renouvelé par l'intercepteur
      const currentToken = await getToken();
      set({ user, token: currentToken, isAuthenticated: true });
      return true;
    } catch {
      // Le refresh a également échoué → déconnexion totale
      await removeToken();
      await removeRefreshToken();
      set({ user: null, token: null, isAuthenticated: false });
      return false;
    }
  },
}));
