import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { setApiBaseUrl } from '@/services/api';
import { requestNotificationPermission } from '@/services/notifications';

const API_URL_KEY = 'anime_sama_api_url';
const EXTERNAL_PLAYER_KEY = 'anime_sama_external_player';

// ─── Notifications ──────────────────────────────────────────────────────────
const NOTIF_ENABLED_KEY       = 'anime_sama_notif_enabled';
const NOTIF_DOWNLOADS_KEY     = 'anime_sama_notif_downloads';
const NOTIF_FAV_EPISODES_KEY  = 'anime_sama_notif_fav_episodes';
const NOTIF_NEW_CATALOGUES_KEY = 'anime_sama_notif_new_catalogues';
const NOTIF_ANY_UPDATE_KEY    = 'anime_sama_notif_any_update';

interface SettingsState {
  apiUrl: string;
  externalPlayer: boolean; // true = ouvrir les vidéos dans un lecteur externe (VLC…)
  ready: boolean; // true une fois loadSettings terminé

  // Interrupteur maître — déclenche la demande de permission OS quand activé.
  notificationsEnabled: boolean;
  // Fin de téléchargement (succès/erreur).
  notifyDownloads:     boolean;
  // Nouvel épisode sur un catalogue favori.
  notifyFavEpisodes:   boolean;
  // Nouveau catalogue ajouté au site.
  notifyNewCatalogues: boolean;
  // N'importe quelle mise à jour de catalogue (bruyant — désactivé par défaut).
  notifyAnyUpdate:     boolean;

  setApiUrl: (url: string) => Promise<void>;
  setExternalPlayer: (v: boolean) => Promise<void>;
  setNotificationsEnabled: (v: boolean) => Promise<boolean>;
  setNotifyDownloads:     (v: boolean) => Promise<void>;
  setNotifyFavEpisodes:   (v: boolean) => Promise<void>;
  setNotifyNewCatalogues: (v: boolean) => Promise<void>;
  setNotifyAnyUpdate:     (v: boolean) => Promise<void>;
  loadSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiUrl:  '',    // vide tant que non configuré
  externalPlayer: false,
  ready:   false,

  notificationsEnabled: false,
  notifyDownloads:      true,
  notifyFavEpisodes:    true,
  notifyNewCatalogues:  false,
  notifyAnyUpdate:      false,

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

  // Retourne l'état effectif (peut rester false si la permission OS est refusée).
  setNotificationsEnabled: async (v) => {
    const effective = v ? await requestNotificationPermission() : false;
    await SecureStore.setItemAsync(NOTIF_ENABLED_KEY, effective ? '1' : '0');
    set({ notificationsEnabled: effective });
    return effective;
  },

  setNotifyDownloads: async (v) => {
    await SecureStore.setItemAsync(NOTIF_DOWNLOADS_KEY, v ? '1' : '0');
    set({ notifyDownloads: v });
  },

  setNotifyFavEpisodes: async (v) => {
    await SecureStore.setItemAsync(NOTIF_FAV_EPISODES_KEY, v ? '1' : '0');
    set({ notifyFavEpisodes: v });
  },

  setNotifyNewCatalogues: async (v) => {
    await SecureStore.setItemAsync(NOTIF_NEW_CATALOGUES_KEY, v ? '1' : '0');
    set({ notifyNewCatalogues: v });
  },

  setNotifyAnyUpdate: async (v) => {
    await SecureStore.setItemAsync(NOTIF_ANY_UPDATE_KEY, v ? '1' : '0');
    set({ notifyAnyUpdate: v });
  },

  loadSettings: async () => {
    const [
      savedUrl, savedExternalPlayer,
      notifEnabled, notifDownloads, notifFavEpisodes, notifNewCatalogues, notifAnyUpdate,
    ] = await Promise.all([
      SecureStore.getItemAsync(API_URL_KEY),
      SecureStore.getItemAsync(EXTERNAL_PLAYER_KEY),
      SecureStore.getItemAsync(NOTIF_ENABLED_KEY),
      SecureStore.getItemAsync(NOTIF_DOWNLOADS_KEY),
      SecureStore.getItemAsync(NOTIF_FAV_EPISODES_KEY),
      SecureStore.getItemAsync(NOTIF_NEW_CATALOGUES_KEY),
      SecureStore.getItemAsync(NOTIF_ANY_UPDATE_KEY),
    ]);
    if (savedUrl) setApiBaseUrl(savedUrl);
    set({
      apiUrl: savedUrl ?? '',
      externalPlayer: savedExternalPlayer === '1',
      notificationsEnabled: notifEnabled === '1',
      notifyDownloads:      notifDownloads === null ? true : notifDownloads === '1',
      notifyFavEpisodes:    notifFavEpisodes === null ? true : notifFavEpisodes === '1',
      notifyNewCatalogues:  notifNewCatalogues === '1',
      notifyAnyUpdate:      notifAnyUpdate === '1',
      ready: true,
    });
  },
}));
