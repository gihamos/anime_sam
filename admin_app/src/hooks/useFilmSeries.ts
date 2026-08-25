import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { TmdbGenresResponse, TmdbMediaType, TmdbSearchResult } from '@/api/types'

export interface TmdbSearchFilters {
  query: string
  mediaType: TmdbMediaType | 'all'
  genreIds: number[]
  anneeMin: string
  anneeMax: string
  pays: string
  page: number
}

function hasAnyFilter(f: TmdbSearchFilters): boolean {
  return !!(f.query.trim() || f.genreIds.length || f.anneeMin || f.anneeMax || f.pays)
}

export function useTmdbSearch(filters: TmdbSearchFilters) {
  return useQuery({
    queryKey: ['tmdb-search', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<TmdbSearchResult[]>('/catalogues/tmdb/rechercher', {
        params: {
          q: filters.query.trim() || undefined,
          type: filters.mediaType === 'all' ? undefined : filters.mediaType,
          genre: filters.genreIds.length ? filters.genreIds.join(',') : undefined,
          annee_min: filters.anneeMin || undefined,
          annee_max: filters.anneeMax || undefined,
          pays: filters.pays || undefined,
          page: filters.page,
        },
      })
      return data
    },
    enabled: hasAnyFilter(filters) && (filters.query.trim().length === 0 || filters.query.trim().length >= 2),
    retry: false,
  })
}

export function useTmdbGenres() {
  return useQuery({
    queryKey: ['tmdb-genres'],
    queryFn: async () => {
      const { data } = await apiClient.get<TmdbGenresResponse>('/catalogues/tmdb/genres')
      return data
    },
    staleTime: 60 * 60_000,
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
