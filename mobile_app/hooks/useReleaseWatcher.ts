import { useEffect, useRef } from 'react';
import * as FileSystem from 'expo-file-system/legacy';
import { useCatalogueList } from './useAnime';
import { useFavoris } from './useFavorites';
import { useSettingsStore } from '@/stores/settingsStore';
import { notifyLocal } from '@/services/notifications';
import { CatalogueSummary } from '@/types';

// Pas de push serveur (Expo Go ne le supporte plus) — la détection de nouveauté se fait
// par diff côté client entre chaque fetch de /mycatalogues/ et le dernier instantané connu,
// stocké en fichier JSON (pas SecureStore : 65+ catalogues dépasseraient sa limite ~2 Ko,
// même motif que scan_chapters.json dans downloadStore.ts).
const SNAPSHOT_FILE = FileSystem.documentDirectory + 'catalogue_snapshot.json';

interface SnapshotEntry {
  updated_at: string;
  total_eps:  number;
}
type Snapshot = Record<string, SnapshotEntry>;

async function loadSnapshot(): Promise<Snapshot> {
  try {
    const info = await FileSystem.getInfoAsync(SNAPSHOT_FILE);
    if (!info.exists) return {};
    const raw = await FileSystem.readAsStringAsync(SNAPSHOT_FILE);
    return JSON.parse(raw) as Snapshot;
  } catch {
    return {};
  }
}

async function saveSnapshot(snap: Snapshot): Promise<void> {
  try {
    await FileSystem.writeAsStringAsync(SNAPSHOT_FILE, JSON.stringify(snap));
  } catch {}
}

function totalEpisodes(cat: CatalogueSummary): number {
  return (cat.saisons ?? []).reduce((sum, s) => sum + (s.total_episodes ?? 0), 0);
}

// Monté une seule fois à la racine (app/_layout.tsx) — actif tant que l'app est ouverte,
// quel que soit l'onglet affiché. Réutilise la query ['catalogues'] déjà chargée par
// l'accueil (React Query déduplique — aucun appel réseau supplémentaire).
export function useReleaseWatcher() {
  const { data: catalogues } = useCatalogueList();
  const { data: favoris } = useFavoris();
  const {
    notificationsEnabled, notifyFavEpisodes, notifyNewCatalogues, notifyAnyUpdate,
  } = useSettingsStore();
  const runningRef = useRef(false);

  useEffect(() => {
    if (!catalogues || !notificationsEnabled || runningRef.current) return;
    runningRef.current = true;

    (async () => {
      try {
        const prev = await loadSnapshot();
        const isFirstRun = Object.keys(prev).length === 0;
        const favSlugs = new Set(favoris?.slugs ?? []);
        const next: Snapshot = {};

        for (const cat of catalogues) {
          const eps = totalEpisodes(cat);
          const prevEntry = prev[cat.slug];
          next[cat.slug] = { updated_at: cat.updated_at ?? '', total_eps: eps };

          // Premier lancement (aucun instantané) : on enregistre juste la base de
          // référence, sinon chaque catalogue existant serait notifié comme "nouveau".
          if (isFirstRun) continue;

          if (!prevEntry) {
            if (notifyNewCatalogues) {
              await notifyLocal('Nouveau catalogue', `${cat.nom} vient d'être ajouté.`);
            }
            continue;
          }

          if (favSlugs.has(cat.slug) && eps > prevEntry.total_eps && notifyFavEpisodes) {
            await notifyLocal('Nouvel épisode', `${cat.nom} a un nouvel épisode disponible.`);
          } else if (notifyAnyUpdate && cat.updated_at && cat.updated_at !== prevEntry.updated_at) {
            await notifyLocal('Mise à jour', `${cat.nom} a été mis à jour.`);
          }
        }

        await saveSnapshot(next);
      } finally {
        runningRef.current = false;
      }
    })();
  }, [catalogues, favoris, notificationsEnabled, notifyFavEpisodes, notifyNewCatalogues, notifyAnyUpdate]);
}
