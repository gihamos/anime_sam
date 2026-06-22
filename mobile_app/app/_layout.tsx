import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSettingsStore } from '@/stores/settingsStore';
import { Colors } from '@/constants/colors';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function RootLayout() {
  const loadSettings = useSettingsStore((s) => s.loadSettings);

  useEffect(() => {
    loadSettings();
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="light" backgroundColor={Colors.background} />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: Colors.background },
            animation: 'slide_from_right',
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="(auth)" options={{ headerShown: false, animation: 'slide_from_bottom' }} />
          <Stack.Screen name="anime/[slug]" options={{ headerShown: false }} />
          <Stack.Screen
            name="player/index"
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
