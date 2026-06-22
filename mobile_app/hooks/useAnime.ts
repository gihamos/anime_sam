import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { catalogueApi } from '@/services/api';
import { SearchFilters, EpisodesResponse } from '@/types';

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
  return useQuery({
    queryKey: ['catalogue', slug],
    queryFn: () => catalogueApi.get(slug),
    staleTime: 10 * 60 * 1000,
  });
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
