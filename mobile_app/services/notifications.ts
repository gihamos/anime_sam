import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

const ANDROID_CHANNEL_ID = 'default';

// Comportement premier plan : les notifs s'affichent même app ouverte (bannière),
// sans son ni badge d'app (le badge d'onglet téléchargements suffit pour ce cas précis).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList:   true,
    shouldPlaySound:  false,
    shouldSetBadge:   false,
  }),
});

export async function ensureAndroidChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
    name: 'Anime Sama',
    importance: Notifications.AndroidImportance.DEFAULT,
  });
}

// Demande la permission OS — à appeler explicitement quand l'utilisateur active le
// réglage "Notifications" (pas au premier lancement, pour ne pas spammer la demande).
export async function requestNotificationPermission(): Promise<boolean> {
  const { status: existing } = await Notifications.getPermissionsAsync();
  let status = existing;
  if (existing !== 'granted') {
    const res = await Notifications.requestPermissionsAsync();
    status = res.status;
  }
  if (status === 'granted') {
    await ensureAndroidChannel();
    return true;
  }
  return false;
}

// Notification locale immédiate (trigger: null) — pas de vraie planification différée,
// Expo Go ne supporte pas les push distantes : tout est déclenché par l'app elle-même
// pendant qu'elle tourne (premier plan ou arrière-plan récent).
export async function notifyLocal(title: string, body: string, data?: Record<string, unknown>): Promise<void> {
  const { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') return;
  try {
    await Notifications.scheduleNotificationAsync({
      content: { title, body, data },
      trigger: null,
    });
  } catch {
    // Best-effort — une notif ratée ne doit jamais faire planter le flux appelant.
  }
}
