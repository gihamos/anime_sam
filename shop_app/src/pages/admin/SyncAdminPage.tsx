import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react'
import {
  useJellyfinSyncStatus, useTriggerJellyfinSync, useJellyfinAutoSync, useUpdateJellyfinAutoSync,
} from '@/hooks/useJellyfinSync'
import { getApiError } from '@/api/client'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

function formatLastSync(iso: string | null): string {
  if (!iso) return 'Aucune synchronisation enregistrée'
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'long', timeStyle: 'short' })
}

export function SyncAdminPage() {
  const { data: status, isLoading } = useJellyfinSyncStatus()
  const triggerSync = useTriggerJellyfinSync()
  const { data: autoSync, isLoading: autoSyncLoading } = useJellyfinAutoSync()
  const updateAutoSync = useUpdateJellyfinAutoSync()

  const [intervalHours, setIntervalHours] = useState('6')

  useEffect(() => {
    if (autoSync) setIntervalHours(String(autoSync.interval_hours))
  }, [autoSync])

  async function handleSync() {
    try {
      await triggerSync.mutateAsync()
      toast.success('Synchronisation Jellyfin déclenchée')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleToggleAutoSync(enabled: boolean) {
    try {
      await updateAutoSync.mutateAsync({ enabled, interval_hours: Number(intervalHours) || 6 })
      toast.success(enabled ? 'Synchronisation automatique activée' : 'Synchronisation automatique désactivée')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleSaveInterval() {
    if (!autoSync) return
    const hours = Number(intervalHours)
    if (!Number.isFinite(hours) || hours < 1) {
      toast.error("L'intervalle doit être d'au moins 1 heure")
      return
    }
    try {
      await updateAutoSync.mutateAsync({ enabled: autoSync.enabled, interval_hours: hours })
      toast.success('Intervalle mis à jour')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Synchronisation Jellyfin</h1>
        <p className="text-sm text-muted-foreground">
          Déclenche la synchronisation de la bibliothèque Jellyfin (extension anime_sama), manuellement
          ou selon une fréquence que vous définissez ici.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">État</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <Skeleton className="h-16 rounded-lg" />
          ) : status?.reachable === false ? (
            <Alert variant="destructive">
              <AlertTriangle className="size-4" />
              <AlertTitle>anime_sam injoignable</AlertTitle>
              <AlertDescription>
                Impossible de récupérer le statut — vérifiez que ANIME_SAM_ADMIN_USERNAME et
                ANIME_SAM_ADMIN_PASSWORD sont configurés dans shop_backend/.env et correspondent à
                un compte admin anime_sam valide.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="size-4 text-primary" />
              <span>Dernière synchronisation : {formatLastSync(status?.last_sync ?? null)}</span>
            </div>
          )}

          <Button onClick={handleSync} disabled={triggerSync.isPending} className="gap-2">
            {triggerSync.isPending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
            Synchroniser maintenant
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Synchronisation automatique</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          {autoSyncLoading ? (
            <Skeleton className="h-16 rounded-lg" />
          ) : (
            <>
              <div className="flex items-center justify-between rounded-md border border-border p-3">
                <div>
                  <p className="text-sm font-medium">Activer</p>
                  <p className="text-xs text-muted-foreground">Déclenche la synchronisation à intervalle régulier, sans intervention.</p>
                </div>
                <Switch
                  checked={autoSync?.enabled ?? false}
                  onCheckedChange={handleToggleAutoSync}
                  disabled={updateAutoSync.isPending}
                />
              </div>

              <div className="flex items-end gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="interval-hours">Intervalle (heures)</Label>
                  <Input
                    id="interval-hours"
                    type="number"
                    min={1}
                    value={intervalHours}
                    onChange={(e) => setIntervalHours(e.target.value)}
                    className="w-32"
                  />
                </div>
                <Button variant="outline" onClick={handleSaveInterval} disabled={updateAutoSync.isPending}>
                  Enregistrer
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
