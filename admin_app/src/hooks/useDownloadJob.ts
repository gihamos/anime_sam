import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient, downloadFileUrl, getApiError } from '@/api/client'
import type { JobStatus } from '@/api/types'

export function useDownloadJob() {
  const [job, setJob] = useState<JobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => () => stopPolling(), [stopPolling])

  const start = useCallback(async (body: Record<string, unknown>) => {
    setError(null)
    setJob(null)
    stopPolling()
    try {
      const { data } = await apiClient.post('/api/download/jobs', body)
      const jobId = data.job_id as string

      pollRef.current = window.setInterval(async () => {
        try {
          const { data: status } = await apiClient.get<JobStatus>(`/api/download/jobs/${jobId}`)
          setJob(status)
          if (status.status === 'ready' || status.status === 'error') stopPolling()
        } catch {
          stopPolling()
        }
      }, 1500)
    } catch (err) {
      setError(getApiError(err))
    }
  }, [stopPolling])

  const cancel = useCallback(async () => {
    stopPolling()
    if (job) {
      await apiClient.delete(`/api/download/jobs/${job.job_id}`).catch(() => {})
    }
    setJob(null)
  }, [job, stopPolling])

  const fileUrl = job?.status === 'ready' ? downloadFileUrl(`/api/download/jobs/${job.job_id}/file`) : null

  return { job, error, start, cancel, fileUrl }
}
