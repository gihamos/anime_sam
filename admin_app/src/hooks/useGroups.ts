import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Group, GroupCreate, GroupUpdate, User } from '@/api/types'

const GROUPS_KEY = ['groups']

export function useGroups() {
  return useQuery({
    queryKey: GROUPS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Group[]>('/admin/api/groups')
      return data
    },
  })
}

export function useCreateGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: GroupCreate) => {
      const { data } = await apiClient.post<Group>('/admin/api/groups', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: GROUPS_KEY }),
  })
}

export function useUpdateGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: GroupUpdate }) => {
      const { data } = await apiClient.put<Group>(`/admin/api/groups/${id}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: GROUPS_KEY }),
  })
}

export function useDeleteGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/admin/api/groups/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: GROUPS_KEY }),
  })
}

export function useGroupMembers(groupId: string | null) {
  return useQuery({
    queryKey: [...GROUPS_KEY, groupId, 'members'],
    queryFn: async () => {
      const { data } = await apiClient.get<User[]>(`/admin/api/groups/${groupId}/members`)
      return data
    },
    enabled: !!groupId,
  })
}

export function useAddGroupMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ groupId, username }: { groupId: string; username: string }) => {
      const { data } = await apiClient.post(`/admin/api/groups/${groupId}/members`, { username })
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: [...GROUPS_KEY, vars.groupId, 'members'] })
      queryClient.invalidateQueries({ queryKey: GROUPS_KEY })
    },
  })
}

export function useRemoveGroupMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ groupId, username }: { groupId: string; username: string }) => {
      await apiClient.delete(`/admin/api/groups/${groupId}/members/${encodeURIComponent(username)}`)
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: [...GROUPS_KEY, vars.groupId, 'members'] })
      queryClient.invalidateQueries({ queryKey: GROUPS_KEY })
    },
  })
}
