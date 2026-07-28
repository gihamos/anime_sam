import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as ExpoSplashScreen from 'expo-splash-screen';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDownloadStore } from '@/stores/downloadStore';
import { useAuthStore } from '@/stores/authStore';
import { useJobPoller } from '@/hooks/useDownloads';
import { Colors } from '@/constants/colors';
import AnimatedSplash from '@/components/SplashScreen';

// Garde le splash natif visible tant que l'animation JS n'a pas pris le relais
// (évite le flash de fond blanc/vide entre le splash natif et le premier rendu JS).
ExpoSplashScreen.preventAutoHideAsync().catch(() => {});

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
  const router = useRouter();
  const { loadSettings, ready, apiUrl } = useSettingsStore();
  const loadFromStorage = useDownloadStore((s) => s.loadFromStorage);
  const checkAuth = useAuthStore((s) => s.checkAuth);
  useJobPoller();

  useEffect(() => {
    async function init() {
      await loadSettings();
      await checkAuth();
      loadFromStorage();
    }
    init();
  }, []);

  // Rediriger vers l'écran de configuration si l'API n'a jamais été configurée
  useEffect(() => {
    if (!ready) return;
    if (!apiUrl) {
      router.replace('/setup');
    }
  }, [ready, apiUrl]);

  return null;
}

export default function RootLayout() {
  const [showSplash, setShowSplash] = useState(true);

  // Le premier layout du root view = le JS a quelque chose à afficher →
  // on masque le splash natif, l'animation JS (même fond) prend le relais sans flash.
  const onRootLayout = useCallback(() => {
    ExpoSplashScreen.hideAsync().catch(() => {});
  }, []);

  // Filet de sécurité : si l'animation (Reanimated) ne se termine jamais pour une
  // raison quelconque, on ne doit jamais bloquer l'app indéfiniment sur le splash.
  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }} onLayout={onRootLayout}>
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
          <Stack.Screen name="setup" options={{ headerShown: false, animation: 'fade' }} />
          <Stack.Screen name="admin/connections" options={{ headerShown: false }} />
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
            name="scan-reader/index"
            options={{
              headerShown: false,
              animation: 'fade',
              presentation: 'fullScreenModal',
            }}
          />
        </Stack>

        {showSplash && (
          <View style={StyleSheet.absoluteFill}>
            <AnimatedSplash onFinish={() => setShowSplash(false)} />
          </View>
        )}
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
