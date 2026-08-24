import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { TmdbMediaType, TmdbSearchResult } from '@/api/types'

export function useTmdbSearch(query: string, mediaType: TmdbMediaType | 'all') {
  return useQuery({
    queryKey: ['tmdb-search', query, mediaType],
    queryFn: async () => {
      const { data } = await apiClient.get<TmdbSearchResult[]>('/catalogues/tmdb/rechercher', {
        params: { q: query, type: mediaType === 'all' ? undefined : mediaType },
      })
      return data
    },
    enabled: query.trim().length >= 2,
    retry: false,
  })
}

export function useAddFromTmdb() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ mediaType, tmdbId }: { mediaType: TmdbMediaType; tmdbId: number }) => {
      const { data } = await apiClient.post(`/catalogues/tmdb/${mediaType}/${tmdbId}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tmdb-search'] })
      queryClient.invalidateQueries({ queryKey: ['catalogues'] })
    },
  })
}
