import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { setApiBaseUrl } from '@/services/api';

const API_URL_KEY = 'anime_sama_api_url';
const EXTERNAL_PLAYER_KEY = 'anime_sama_external_player';

interface SettingsState {
  apiUrl: string;
  externalPlayer: boolean; // true = ouvrir les vidéos dans un lecteur externe (VLC…)
  ready: boolean; // true une fois loadSettings terminé
  setApiUrl: (url: string) => Promise<void>;
  setExternalPlayer: (v: boolean) => Promise<void>;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiUrl:  '',    // vide tant que non configuré
  externalPlayer: false,
  ready:   false,

  setApiUrl: async (url) => {
    const clean = url.trim().replace(/\/$/, '');
    await SecureStore.setItemAsync(API_URL_KEY, clean);
    setApiBaseUrl(clean);
    set({ apiUrl: clean });
  },

  setExternalPlayer: async (v) => {
    await SecureStore.setItemAsync(EXTERNAL_PLAYER_KEY, v ? '1' : '0');
    set({ externalPlayer: v });
  },

  loadSettings: async () => {
    const [savedUrl, savedExternalPlayer] = await Promise.all([
      SecureStore.getItemAsync(API_URL_KEY),
      SecureStore.getItemAsync(EXTERNAL_PLAYER_KEY),
    ]);
    if (savedUrl) setApiBaseUrl(savedUrl);
    set({
      apiUrl: savedUrl ?? '',
      externalPlayer: savedExternalPlayer === '1',
      ready: true,
    });
  },
}));
