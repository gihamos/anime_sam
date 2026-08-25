import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { SiteSearchResult } from '@/api/types'

export interface SiteSearchFilters {
  search: string
  types: string[]
  langues: string[]
  statuts: string[]
  genres: string[]
  anneeMin: string
  anneeMax: string
  page: number
}

function hasAnyFilter(f: SiteSearchFilters): boolean {
  return !!(
    f.search.trim() ||
    f.types.length ||
    f.langues.length ||
    f.statuts.length ||
    f.genres.length ||
    f.anneeMin ||
    f.anneeMax
  )
}

export function useSiteSearchAdvanced(filters: SiteSearchFilters) {
  return useQuery({
    queryKey: ['site-search-advanced', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<SiteSearchResult[]>('/catalogues/site/rechercher', {
        params: {
          search: filters.search || undefined,
          type: filters.types.length ? filters.types.join(',') : undefined,
          langue: filters.langues.length ? filters.langues.join(',') : undefined,
          statut: filters.statuts.length ? filters.statuts.join(',') : undefined,
          genre: filters.genres.length ? filters.genres.join(',') : undefined,
          annee_min: filters.anneeMin || undefined,
          annee_max: filters.anneeMax || undefined,
          page: filters.page,
        },
      })
      return data
    },
    enabled: hasAnyFilter(filters),
    retry: false,
  })
}

export function useGenres() {
  return useQuery({
    queryKey: ['genres'],
    queryFn: async () => {
      const { data } = await apiClient.get<string[]>('/admin/api/genres')
      return data
    },
    staleTime: 5 * 60_000,
  })
}
