import { useEffect, useCallback, useRef, useState } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { catalogueApi, getApiError } from '@/services/api';
import { SearchFilters, EpisodesResponse, SyncStatus } from '@/types';
import {
  loadCatalogueCache,
  saveCatalogueCache,
  CATALOGUE_CACHE_TTL,
} from '@/services/catalogueCache';

export function useCatalogueList() {
  return useQuery({
    queryKey: ['catalogues'],
    queryFn: catalogueApi.list,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSimilarCatalogues(slug: string) {
  return useQuery({
    queryKey: ['similar', slug],
    queryFn: () => catalogueApi.getSimilar(slug),
    enabled: !!slug,
    staleTime: 10 * 60 * 1000,
  });
}

export function useCatalogueSearch(filters: SearchFilters, enabled = true) {
  return useQuery({
    queryKey: ['catalogues', 'search', filters],
    queryFn: () => catalogueApi.search(filters),
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCatalogue(slug: string) {
  const queryClient = useQueryClient();

  // Injecter le cache disque dans React Query avant que le réseau réponde.
  // Si les données sont encore fraîches (< TTL), React Query n'enverra pas de requête.
  useEffect(() => {
    let cancelled = false;
    loadCatalogueCache(slug).then((entry) => {
      if (cancelled || !entry) return;
      // Ne pas écraser si React Query a déjà des données (réseau plus rapide que disque)
      const state = queryClient.getQueryState(['catalogue', slug]);
      if (!state?.data) {
        queryClient.setQueryData(['catalogue', slug], entry.data, {
          updatedAt: entry.cached_at,
        });
      }
    });
    return () => { cancelled = true; };
  }, [slug, queryClient]);

  return useQuery({
    queryKey: ['catalogue', slug],
    queryFn: async () => {
      const data = await catalogueApi.get(slug);
      saveCatalogueCache(slug, data); // fire-and-forget — ne bloque pas l'UI
      return data;
    },
    staleTime: CATALOGUE_CACHE_TTL, // 1 h : pas de refetch si cache récent
  });
}

/**
 * Force la re-synchronisation du catalogue depuis le serveur.
 * Met à jour le cache disque en arrière-plan (via le queryFn de useCatalogue).
 * Disponible pour tous les utilisateurs authentifiés.
 */
export function useSyncCatalogue(slug: string) {
  const queryClient = useQueryClient();
  return useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['catalogue', slug] });
  }, [slug, queryClient]);
}

/**
 * Démarre la synchronisation complète du contenu (saisons/films/scans) et suit
 * sa progression par polling jusqu'à la fin, puis invalide le cache du catalogue
 * pour que les données fraîchement synchronisées (ex: chapitres de scan) apparaissent.
 * Nécessite la permission `can_sync`.
 */
export function useSyncContent(slug: string) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = undefined;
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const poll = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const s = await catalogueApi.getSyncStatus(slug);
        setStatus(s);
        if (s.status !== 'syncing') {
          stopPolling();
          queryClient.invalidateQueries({ queryKey: ['catalogue', slug] });
        }
      } catch {
        stopPolling();
      }
    }, 2500);
  }, [slug, stopPolling, queryClient]);

  const start = useCallback(async () => {
    setError(null);
    try {
      await catalogueApi.syncContent(slug);
      poll();
    } catch (err) {
      // 409 = déjà en cours (ailleurs) → on observe simplement la progression existante.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        poll();
        return;
      }
      setError(getApiError(err));
    }
  }, [slug, poll]);

  return { start, status, error, isSyncing: status?.status === 'syncing' };
}

export function useRefreshCatalogue(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => catalogueApi.refresh(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogue', slug] });
    },
  });
}

// Épisodes on-demand — scraping côté serveur, peut prendre 5-30s
export function useEpisodes(
  slug: string,
  saisonSlug: string,
  lang: string,
  enabled: boolean,
) {
  return useQuery<EpisodesResponse>({
    queryKey: ['episodes', slug, saisonSlug, lang],
    queryFn: () => catalogueApi.getEpisodes(slug, saisonSlug, lang),
    enabled: enabled && !!slug && !!saisonSlug && !!lang,
    staleTime: 30 * 60 * 1000, // cache 30 min — le scraping est lent
    // Pas de retry auto : un scraping live qui vient d'échouer/timeout ne sera pas
    // plus rapide en le relançant à l'identique, et ça double la charge serveur.
    // L'utilisateur a un bouton "Réessayer" manuel en cas d'échec.
    retry: false,
  });
}
