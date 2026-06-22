import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { useAuthStore } from '@/stores/authStore';
import { useJobPoller } from '@/hooks/useDownloads';
import { Colors } from '@/constants/colors';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// Composant séparé pour le polling (doit être dans le QueryClientProvider)
function AppInit() {
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const loadFromStorage = useDownloadStore((s) => s.loadFromStorage);
  const checkAuth = useAuthStore((s) => s.checkAuth);
  useJobPoller();

  useEffect(() => {
    // Ordre important : d'abord l'URL de l'API, puis la restauration de session
    async function init() {
      await loadSettings();
      await checkAuth();
      loadFromStorage();
    }
    init();
  }, []);

  return null;
}

export default function RootLayout() {

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <AppInit />
        <StatusBar style="light" backgroundColor={Colors.background} />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: Colors.background },
            animation: 'slide_from_right',
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="anime/[slug]" options={{ headerShown: false }} />
          <Stack.Screen
            name="player/index"
            options={{
              headerShown: false,
              animation: 'fade',
              presentation: 'fullScreenModal',
            }}
          />
          <Stack.Screen
            name="scan-reader"
            options={{
              headerShown: false,
              animation: 'fade',
              presentation: 'fullScreenModal',
            }}
          />
        </Stack>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
