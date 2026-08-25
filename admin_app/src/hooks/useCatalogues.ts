import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type {
  BulkResult,
  CatalogueAdminSummary,
  CatalogueContenu,
  CatalogueDetail,
  CatalogueUpdate,
  CatalogueVisibility,
  SiteSearchResult,
} from '@/api/types'

const CATALOGUES_KEY = ['catalogues']

export function useCatalogues() {
  return useQuery({
    queryKey: CATALOGUES_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<CatalogueAdminSummary[]>('/admin/api/catalogues')
      return data
    },
  })
}

export function useCatalogueDetail(slug: string | null) {
  return useQuery({
    queryKey: [...CATALOGUES_KEY, slug, 'detail'],
    queryFn: async () => {
      const { data } = await apiClient.get<CatalogueDetail>(`/admin/api/catalogues/${encodeURIComponent(slug!)}`)
      return data
    },
    enabled: !!slug,
  })
}

export function useCatalogueContenu(slug: string | null) {
  return useQuery({
    queryKey: [...CATALOGUES_KEY, slug, 'contenu'],
    queryFn: async () => {
      const { data } = await apiClient.get<CatalogueContenu>(`/admin/api/catalogues/${encodeURIComponent(slug!)}/contenu`)
      return data
    },
    enabled: !!slug,
  })
}

export function useSiteSearch(query: string) {
  return useQuery({
    queryKey: ['site-search', query],
    queryFn: async () => {
      const { data } = await apiClient.get<SiteSearchResult[]>('/catalogues/site/rechercher', {
        params: { search: query },
      })
      return data
    },
    enabled: query.trim().length >= 2,
    retry: false,
  })
}

export function useAddCatalogueByUrl() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (url: string) => {
      const { data } = await apiClient.get(`/catalogues/${encodeURIComponent(slugFromUrl(url))}`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

function slugFromUrl(input: string): string {
  const trimmed = input.trim().replace(/\/$/, '')
  const parts = trimmed.split('/')
  return parts[parts.length - 1] || trimmed
}

export function useUpdateCatalogueMeta() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ slug, body }: { slug: string; body: CatalogueUpdate }) => {
      const { data } = await apiClient.put(`/admin/api/catalogues/${encodeURIComponent(slug)}`, body)
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY })
      queryClient.invalidateQueries({ queryKey: [...CATALOGUES_KEY, vars.slug, 'detail'] })
    },
  })
}

export function useUpdateCatalogueVisibility() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ slug, body }: { slug: string; body: CatalogueVisibility }) => {
      const { data } = await apiClient.put(`/admin/api/catalogues/${encodeURIComponent(slug)}/visibility`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

export function useDeleteCatalogue() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slug: string) => {
      await apiClient.delete(`/admin/api/catalogues/${encodeURIComponent(slug)}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

export function useRefreshCatalogue() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slug: string) => {
      const { data } = await apiClient.post(`/catalogues/${encodeURIComponent(slug)}/rafraichir`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

export function useBulkDeleteCatalogues() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slugs: string[]) => {
      const { data } = await apiClient.post<BulkResult>('/admin/api/catalogues/bulk-delete', { slugs })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

export function useBulkRefreshCatalogues() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (slugs: string[]) => {
      const { data } = await apiClient.post<BulkResult>('/admin/api/catalogues/bulk-rafraichir', { slugs })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}

export function useBulkUpdateVisibility() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ slugs, isPublic }: { slugs: string[]; isPublic: boolean }) => {
      const { data } = await apiClient.put<BulkResult>('/admin/api/catalogues/bulk-visibility', {
        slugs,
        is_public: isPublic,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CATALOGUES_KEY }),
  })
}
