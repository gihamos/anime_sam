import { useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { catalogueApi } from '@/services/api';
import { SearchFilters, EpisodesResponse } from '@/types';
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

export function useCatalogueSearch(filters: SearchFilters, enabled = true) {
  return useQuery({
    queryKey: ['catalogues', 'search', filters],
    queryFn: () => catalogueApi.search(filters),
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

export function useSiteSearch(q: string, enabled = false) {
  return useQuery({
    queryKey: ['site-search', q],
    queryFn: () => catalogueApi.searchSite(q),
    enabled: enabled && q.length >= 2,
    staleTime: 60 * 1000,
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

export function useSyncContent(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => catalogueApi.syncContent(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalogue', slug] });
    },
  });
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
    retry: 1,
  });
}
