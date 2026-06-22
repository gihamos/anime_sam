import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { setApiBaseUrl } from '@/services/api';

const API_URL_KEY = 'anime_sama_api_url';

interface SettingsState {
  apiUrl: string;
  ready: boolean; // true une fois loadSettings terminé
  setApiUrl: (url: string) => Promise<void>;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiUrl:  '',    // vide tant que non configuré
  ready:   false,

  setApiUrl: async (url) => {
    const clean = url.trim().replace(/\/$/, '');
    await SecureStore.setItemAsync(API_URL_KEY, clean);
    setApiBaseUrl(clean);
    set({ apiUrl: clean });
  },

  loadSettings: async () => {
    const savedUrl = await SecureStore.getItemAsync(API_URL_KEY);
    if (savedUrl) {
      setApiBaseUrl(savedUrl);
      set({ apiUrl: savedUrl, ready: true });
    } else {
      set({ ready: true }); // pas d'URL → onboarding requis
    }
  },
}));
