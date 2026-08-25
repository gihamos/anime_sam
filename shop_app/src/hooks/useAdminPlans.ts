import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { LibraryFolder, PlanAdmin } from '@/api/types'

const PLANS_KEY = ['admin', 'plans']

export interface PlanFormValues {
  slug: string
  name: string
  description: string
  price: number
  currency: string
  billing_period: string
  jellyfin_library_folder_ids: string[]
  jellyfin_library_names: string[]
  max_devices: number
  allow_downloads: boolean
  is_active: boolean
  sort_order: number
}

export function useAdminPlans() {
  return useQuery({
    queryKey: PLANS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<PlanAdmin[]>('/admin/api/plans')
      return data
    },
  })
}

export function useLibraryFolders() {
  return useQuery({
    queryKey: ['admin', 'jellyfin', 'library-folders'],
    queryFn: async () => {
      const { data } = await apiClient.get<LibraryFolder[]>('/admin/api/jellyfin/library-folders')
      return data
    },
  })
}

export function useCreatePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PlanFormValues) => {
      const { data } = await apiClient.post<PlanAdmin>('/admin/api/plans', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PLANS_KEY }),
  })
}

export function useUpdatePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: Partial<PlanFormValues> }) => {
      const { data } = await apiClient.put<{ plan: PlanAdmin; warning: string | null }>(`/admin/api/plans/${id}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PLANS_KEY }),
  })
}

export function useDeletePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/admin/api/plans/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PLANS_KEY }),
  })
}
