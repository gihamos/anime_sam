import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { User, UserCreate, UserUpdate } from '@/api/types'

const USERS_KEY = ['users']

export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<User[]>('/auth/users')
      return data
    },
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: UserCreate) => {
      const { data } = await apiClient.post<User>('/auth/register', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ username, body }: { username: string; body: UserUpdate }) => {
      const { data } = await apiClient.put<User>(`/auth/users/${encodeURIComponent(username)}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (username: string) => {
      await apiClient.delete(`/auth/users/${encodeURIComponent(username)}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  })
}

export function useUpdateDownloadPerms() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      username,
      canDownload,
      forbiddenSlugs,
    }: {
      username: string
      canDownload: boolean
      forbiddenSlugs: string[]
    }) => {
      const { data } = await apiClient.put(`/admin/api/users/${encodeURIComponent(username)}/dl-perms`, {
        can_download: canDownload,
        download_forbidden_slugs: forbiddenSlugs,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  })
}
