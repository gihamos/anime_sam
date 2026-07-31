import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, FontSize } from '@/constants/colors';
import { useDownloadStore } from '@/stores/downloadStore';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// Base de la barre hors zone système — la hauteur/marge basse réelle est complétée par
// insets.bottom (voir plus bas) au lieu d'une valeur fixe.
const TAB_BAR_BASE_HEIGHT = 56;

export default function TabsLayout() {
  const jobs = useDownloadStore((s) => s.jobs);
  const activeDownloads = jobs.filter(
    (j) => j.status === 'pending' || j.status === 'downloading'
  ).length;
  // insets.bottom = hauteur réelle de la barre de navigation système Android (3 boutons,
  // geste, ou barre custom OEM) / de l'encoche iOS — variable selon l'appareil. Une valeur
  // fixe (ancien code) laisse la barre système recouvrir les icônes sur les appareils dont
  // la barre est plus haute que prévu. react-native-safe-area-context lit ça nativement via
  // WindowInsets (Android) / safeAreaInsets (iOS), déjà fourni par expo-router à la racine.
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.surface,
          borderTopColor: Colors.border,
          borderTopWidth: 1,
          height: TAB_BAR_BASE_HEIGHT + insets.bottom,
          paddingBottom: insets.bottom,
          paddingTop: 8,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarLabelStyle: {
          fontSize: FontSize.xs,
          fontWeight: '600',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Accueil',
          tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: 'Recherche',
          tabBarIcon: ({ color, size }) => <Ionicons name="search" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="favoris"
        options={{
          title: 'Favoris',
          tabBarIcon: ({ color, size }) => <Ionicons name="heart" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="downloads"
        options={{
          title: 'Téléch.',
          tabBarIcon: ({ color, size }) => <Ionicons name="download" size={size} color={color} />,
          tabBarBadge: activeDownloads > 0 ? activeDownloads : undefined,
          tabBarBadgeStyle: { backgroundColor: Colors.primary, fontSize: FontSize.xs - 2 },
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profil',
          tabBarIcon: ({ color, size }) => <Ionicons name="person" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
}
