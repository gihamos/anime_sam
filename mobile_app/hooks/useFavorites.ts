import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { favorisApi } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { FavorisResponse, RecommendationItem } from '@/types';

export function useFavoris() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ['favoris'],
    queryFn: favorisApi.get,
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}

export function useIsFavori(slug: string): boolean {
  const { data } = useFavoris();
  return data?.slugs.includes(slug) ?? false;
}

export function useToggleFavori(slug: string) {
  const queryClient = useQueryClient();
  const isFavori = useIsFavori(slug);

  return useMutation({
    mutationFn: () => isFavori ? favorisApi.remove(slug) : favorisApi.add(slug),
    // Optimistic update
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['favoris'] });
      const prev = queryClient.getQueryData<{ slugs: string[]; catalogues: any[] }>(['favoris']);
      queryClient.setQueryData(['favoris'], (old: any) => {
        if (!old) return old;
        const slugs = isFavori
          ? old.slugs.filter((s: string) => s !== slug)
          : [...old.slugs, slug];
        const catalogues = isFavori
          ? old.catalogues.filter((c: any) => c.slug !== slug)
          : old.catalogues;
        return { slugs, catalogues };
      });
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(['favoris'], ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['favoris'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useRecommendations() {
  const { isAuthenticated } = useAuthStore();
  return useQuery<RecommendationItem[]>({
    queryKey: ['recommendations'],
    queryFn: favorisApi.recommendations,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}
