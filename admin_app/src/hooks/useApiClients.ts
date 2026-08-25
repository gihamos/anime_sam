import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { ApiClient, ApiClientCreated, ApiClientPermissions, SecretRegenerated } from '@/api/types'

const CLIENTS_KEY = ['api-clients']

export function useApiClients() {
  return useQuery({
    queryKey: CLIENTS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<ApiClient[]>('/admin/api/clients')
      return data
    },
  })
}

export function useCreateApiClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { name: string; description?: string; permissions: ApiClientPermissions }) => {
      const { data } = await apiClient.post<ApiClientCreated>('/admin/api/clients', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  })
}

export function useUpdateApiClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      clientId,
      body,
    }: {
      clientId: string
      body: { name?: string; description?: string; is_active?: boolean; permissions?: ApiClientPermissions }
    }) => {
      const { data } = await apiClient.put(`/admin/api/clients/${clientId}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  })
}

export function useDeleteApiClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (clientId: string) => {
      await apiClient.delete(`/admin/api/clients/${clientId}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  })
}

export function useRegenerateApiClientSecret() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (clientId: string) => {
      const { data } = await apiClient.post<SecretRegenerated>(`/admin/api/clients/${clientId}/regenerate-secret`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  })
}
