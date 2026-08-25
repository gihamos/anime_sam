import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { PlanningJour, Schedule, ScheduleCreate, ScheduleUpdate, SyncHistoryEntry } from '@/api/types'

const SCHEDULES_KEY = ['schedules']

export function useSchedules() {
  return useQuery({
    queryKey: SCHEDULES_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Schedule[]>('/admin/api/schedules')
      return data
    },
  })
}

export function useCreateSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ScheduleCreate) => {
      const { data } = await apiClient.post<Schedule>('/admin/api/schedules', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SCHEDULES_KEY }),
  })
}

export function useUpdateSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: ScheduleUpdate }) => {
      const { data } = await apiClient.put<Schedule>(`/admin/api/schedules/${id}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SCHEDULES_KEY }),
  })
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/admin/api/schedules/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SCHEDULES_KEY }),
  })
}

export function useRunScheduleNow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post(`/admin/api/schedules/${id}/run`)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SCHEDULES_KEY }),
  })
}

export function usePlanning() {
  return useQuery({
    queryKey: ['planning'],
    queryFn: async () => {
      const { data } = await apiClient.get<PlanningJour[]>('/planning/')
      return data
    },
    staleTime: 5 * 60_000,
  })
}

export function useSyncHistory() {
  return useQuery({
    queryKey: ['sync-history'],
    queryFn: async () => {
      const { data } = await apiClient.get<SyncHistoryEntry[]>('/admin/api/history')
      return data
    },
  })
}

export function useClearSyncHistory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete('/admin/api/history')
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sync-history'] }),
  })
}
