import { useState } from 'react'
import { toast } from 'sonner'
import { Settings, Trash2 } from 'lucide-react'
import { useClearDownloadHistory, useDlQuotas, useDownloadHistory } from '@/hooks/useDownloadsAdmin'
import { getApiError } from '@/api/client'
import type { DlQuota } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { DlQuotaDialog } from './downloads/DlQuotaDialog'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  const units = ['Ko', 'Mo', 'Go', 'To']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i++
  }
  return `${value.toFixed(1)} ${units[i]}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export function DownloadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Téléchargements</h1>
        <p className="text-sm text-muted-foreground">Historique et quotas de téléchargement.</p>
      </div>

      <Tabs defaultValue="historique">
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="historique">Historique</TabsTrigger>
            <TabsTrigger value="quotas">Quotas</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="historique" className="pt-4">
          <HistoryTab />
        </TabsContent>
        <TabsContent value="quotas" className="pt-4">
          <QuotasTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function HistoryTab() {
  const { data: history = [], isLoading } = useDownloadHistory()
  const clearHistory = useClearDownloadHistory()

  async function handleClear() {
    try {
      await clearHistory.mutateAsync()
      toast.success('Historique vidé')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">Derniers téléchargements (200 max)</p>
        <Button size="sm" variant="destructive" onClick={handleClear} disabled={clearHistory.isPending}>
          <Trash2 className="size-3.5" />
          Vider
        </Button>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Utilisateur</TableHead>
              <TableHead>Catalogue</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Fichiers</TableHead>
              <TableHead>Taille</TableHead>
              <TableHead>Détails</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}
            {!isLoading && history.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">Aucun téléchargement.</TableCell>
              </TableRow>
            )}
            {history.map((h, i) => (
              <TableRow key={i}>
                <TableCell className="font-medium">{h.username}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.slug}</TableCell>
                <TableCell><Badge variant="secondary">{h.type ?? '—'}</Badge></TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.nb_files}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatBytes(h.size_bytes)}</TableCell>
                <TableCell className="max-w-56 truncate text-sm text-muted-foreground" title={h.details}>{h.details}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(h.date)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function QuotasTab() {
  const { data: quotas = [], isLoading } = useDlQuotas()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeUsername, setActiveUsername] = useState<string | null>(null)
  const [activeQuota, setActiveQuota] = useState<DlQuota | null>(null)

  function openQuota(username: string, quota: DlQuota | null) {
    setActiveUsername(username)
    setActiveQuota(quota)
    setDialogOpen(true)
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Quotas par utilisateur — <code>__default__</code> est la règle globale
        </p>
        <Button size="sm" onClick={() => openQuota('__default__', quotas.find((q) => q.username === '__default__') ?? null)}>
          <Settings className="size-3.5" />
          Quota global
        </Button>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Utilisateur</TableHead>
              <TableHead>Fichiers / 24h</TableHead>
              <TableHead>Go / 24h</TableHead>
              <TableHead>Téléchargement</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}
            {!isLoading && quotas.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">Aucun quota configuré.</TableCell>
              </TableRow>
            )}
            {quotas.map((q) => (
              <TableRow key={q.username}>
                <TableCell className="font-medium">{q.username}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{q.max_files_per_day}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{q.max_gb_per_day}</TableCell>
                <TableCell>
                  {q.can_download ? <Badge className="bg-success text-success-foreground">Autorisé</Badge> : <Badge variant="destructive">Bloqué</Badge>}
                </TableCell>
                <TableCell>
                  <Button size="sm" variant="ghost" onClick={() => openQuota(q.username, q)}>Modifier</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <DlQuotaDialog open={dialogOpen} onOpenChange={setDialogOpen} username={activeUsername} quota={activeQuota} />
    </div>
  )
}
