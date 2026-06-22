import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { catalogueApi } from '@/services/api';
import { SearchFilters } from '@/types';

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
