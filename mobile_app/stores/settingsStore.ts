import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { setApiBaseUrl, DEFAULT_API_URL } from '@/services/api';

const API_URL_KEY = 'anime_sama_api_url';

interface SettingsState {
  apiUrl: string;
  setApiUrl: (url: string) => Promise<void>;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiUrl: DEFAULT_API_URL,

  setApiUrl: async (url) => {
    await SecureStore.setItemAsync(API_URL_KEY, url);
    setApiBaseUrl(url);
    set({ apiUrl: url });
  },

  loadSettings: async () => {
    const savedUrl = await SecureStore.getItemAsync(API_URL_KEY);
    if (savedUrl) {
      setApiBaseUrl(savedUrl);
      set({ apiUrl: savedUrl });
    }
  },
}));
