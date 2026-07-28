/**
 * Cache disque des catalogues — FileSystem par slug.
 *
 * Stratégie stale-while-revalidate :
 *  - Données < TTL → servies directement, pas de refetch réseau
 *  - Données ≥ TTL → affichées immédiatement, refetch réseau en arrière-plan
 *  - Pas de cache   → loading normal jusqu'à la réponse réseau
 *
 * TTL : 1 heure. Le bouton "Synchroniser" invalide le cache à la demande.
 */

import * as FileSystem from 'expo-file-system/legacy';
import { Catalogue } from '@/types';

const CACHE_DIR = FileSystem.documentDirectory + 'catalogue_cache/';
export const CATALOGUE_CACHE_TTL = 60 * 60 * 1000; // 1 heure

export interface CacheEntry {
  data: Catalogue;
  cached_at: number;
}

export async function loadCatalogueCache(slug: string): Promise<CacheEntry | null> {
  try {
    const path = `${CACHE_DIR}${slug}.json`;
    const info = await FileSystem.getInfoAsync(path);
    if (!info.exists) return null;
    const raw = await FileSystem.readAsStringAsync(path);
    return JSON.parse(raw) as CacheEntry;
  } catch {
    return null;
  }
}

export async function saveCatalogueCache(slug: string, data: Catalogue): Promise<void> {
  try {
    await FileSystem.makeDirectoryAsync(CACHE_DIR, { intermediates: true });
    const entry: CacheEntry = { data, cached_at: Date.now() };
    await FileSystem.writeAsStringAsync(`${CACHE_DIR}${slug}.json`, JSON.stringify(entry));
  } catch {}
}

export async function deleteCatalogueCache(slug: string): Promise<void> {
  try {
    await FileSystem.deleteAsync(`${CACHE_DIR}${slug}.json`, { idempotent: true });
  } catch {}
}

/** Formate l'âge du cache en texte lisible. */
export function formatCacheAge(cached_at: number): string {
  const diffMs  = Date.now() - cached_at;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1)  return 'À l\'instant';
  if (diffMin < 60) return `Il y a ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24)   return `Il y a ${diffH} h`;
  const diffD = Math.floor(diffH / 24);
  return `Il y a ${diffD} j`;
}
