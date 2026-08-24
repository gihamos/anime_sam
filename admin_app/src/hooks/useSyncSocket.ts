import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient, getToken, wsBaseUrl } from '@/api/client'

export interface SyncEvent {
  type: string
  [key: string]: unknown
}

type SyncPhase = 'idle' | 'connecting' | 'running' | 'completed' | 'error'

export function useSyncSocket(slug: string | null) {
  const [phase, setPhase] = useState<SyncPhase>('idle')
  const [progress, setProgress] = useState(0)
  const [log, setLog] = useState<SyncEvent[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)

  const disconnect = useCallback(() => {
    socketRef.current?.close()
    socketRef.current = null
  }, [])

  const start = useCallback(() => {
    if (!slug) return
    disconnect()
    setLog([])
    setProgress(0)
    setErrorMessage(null)
    setPhase('connecting')

    const token = getToken()
    const ws = new WebSocket(`${wsBaseUrl()}/catalogues/${encodeURIComponent(slug)}/sync-content/ws?token=${encodeURIComponent(token ?? '')}`)
    socketRef.current = ws

    ws.onopen = () => setPhase('running')
    ws.onmessage = (event) => {
      const data: SyncEvent = JSON.parse(event.data)
      if (data.type === 'ping') return
      setLog((prev) => [...prev, data])

      if (typeof data.progress === 'number') setProgress(data.progress)
      if (data.type === 'completed') {
        setPhase('completed')
        setProgress(100)
      } else if (data.type === 'error') {
        setPhase('error')
        setErrorMessage(typeof data.message === 'string' ? data.message : String(data.reason ?? 'Erreur de synchronisation'))
      } else if (data.type === 'cancelled') {
        setPhase('idle')
      }
    }
    ws.onerror = () => setPhase('error')
    ws.onclose = () => {
      socketRef.current = null
    }
  }, [slug, disconnect])

  useEffect(() => () => disconnect(), [disconnect])

  const pause = useCallback(async () => {
    if (!slug) return
    await apiClient.post(`/catalogues/${encodeURIComponent(slug)}/sync-content/pause`)
  }, [slug])

  const resume = useCallback(async () => {
    if (!slug) return
    await apiClient.post(`/catalogues/${encodeURIComponent(slug)}/sync-content/resume`)
  }, [slug])

  const cancel = useCallback(async () => {
    if (!slug) return
    await apiClient.delete(`/catalogues/${encodeURIComponent(slug)}/sync-content`)
    disconnect()
    setPhase('idle')
  }, [slug, disconnect])

  return { phase, progress, log, errorMessage, start, pause, resume, cancel, disconnect }
}
