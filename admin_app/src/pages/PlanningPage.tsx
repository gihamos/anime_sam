import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Clock, Loader2, Play, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useDeleteSchedule, usePlanning, useRunScheduleNow, useSchedules, useSyncHistory, useClearSyncHistory } from '@/hooks/useSchedules'
import { getApiError } from '@/api/client'
import type { PlanningJour, Schedule } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { ScheduleFormDialog } from './planning/ScheduleFormDialog'

const FREQ_LABELS: Record<string, string> = {
  daily: 'Quotidien',
  weekly: 'Hebdomadaire',
  biweekly: 'Bi-hebdomadaire',
  monthly: 'Mensuel',
  custom: 'Personnalisé',
}

function formatSchedule(s: Schedule): string {
  const t = `${String(s.hour).padStart(2, '0')}h${String(s.minute).padStart(2, '0')}`
  const days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
  switch (s.frequency) {
    case 'daily': return `Chaque jour à ${t} UTC`
    case 'weekly': return `Chaque ${days[s.day_of_week ?? 0]} à ${t} UTC`
    case 'biweekly': return `Toutes les 2 sem. (${days[s.day_of_week ?? 0]}) à ${t} UTC`
    case 'monthly': return `Le ${s.day_of_month} du mois à ${t} UTC`
    case 'custom': return `Tous les ${s.interval_days} jours à ${t} UTC`
    default: return FREQ_LABELS[s.frequency] ?? s.frequency
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export function PlanningPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Planification</h1>
        <p className="text-sm text-muted-foreground">Sorties de la semaine, synchronisations automatiques, historique.</p>
      </div>

      <Tabs defaultValue="sorties">
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="sorties">Sorties de la semaine</TabsTrigger>
            <TabsTrigger value="programmations">Programmations auto</TabsTrigger>
            <TabsTrigger value="historique">Historique des syncs</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="sorties" className="pt-4">
          <PlanningTab />
        </TabsContent>
        <TabsContent value="programmations" className="pt-4">
          <SchedulesTab />
        </TabsContent>
        <TabsContent value="historique" className="pt-4">
          <HistoryTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function PlanningTab() {
  const { data: planning, isLoading, isError, error, refetch, isFetching } = usePlanning()
  const { data: catalogues = [] } = useCatalogues()
  const knownSlugs = useMemo(() => new Set(catalogues.map((c) => c.slug)), [catalogues])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">Source : anime-sama.to · heure locale</p>
        <Button size="sm" variant="secondary" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
          Actualiser
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      {isError && <p className="text-sm text-destructive">{getApiError(error)}</p>}

      {planning && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {planning.map((jour: PlanningJour) => (
            <div key={jour.jour} className="space-y-2 rounded-lg border border-border p-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{jour.jour} {jour.date}</p>
              <div className="space-y-1.5">
                {jour.animes.map((a, i) => (
                  <a
                    key={i}
                    href={a.url_saison || a.url}
                    target="_blank"
                    rel="noreferrer"
                    className={`block rounded-md border px-2 py-1.5 text-xs transition-colors hover:border-primary/40 ${knownSlugs.has(a.slug) ? 'border-success/30 bg-success/10' : 'border-border bg-secondary'}`}
                  >
                    <p className="line-clamp-1 font-medium">{a.titre}</p>
                    <p className="text-muted-foreground">{a.heure} · {a.saison_info}</p>
                  </a>
                ))}
                {jour.animes.length === 0 && <p className="text-xs text-muted-foreground">Aucune sortie.</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SchedulesTab() {
  const { data: schedules = [], isLoading } = useSchedules()
  const deleteSchedule = useDeleteSchedule()
  const runNow = useRunScheduleNow()

  const [formOpen, setFormOpen] = useState(false)
  const [activeSchedule, setActiveSchedule] = useState<Schedule | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Schedule | null>(null)

  function openEdit(s: Schedule) {
    setActiveSchedule(s)
    setFormOpen(true)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteSchedule.mutateAsync(deleteTarget.id)
      toast.success('Programmation supprimée')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleRunNow(s: Schedule) {
    try {
      await runNow.mutateAsync(s.id)
      toast.success(`Synchronisation de « ${s.slug} » lancée`)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setActiveSchedule(null); setFormOpen(true) }}>
          <Plus className="size-3.5" />
          Nouvelle
        </Button>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Catalogue</TableHead>
              <TableHead>Fréquence</TableHead>
              <TableHead>Prochaine exécution</TableHead>
              <TableHead>Dernière exécution</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead className="w-40" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}
            {!isLoading && schedules.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">Aucune programmation.</TableCell>
              </TableRow>
            )}
            {schedules.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-medium">{s.slug}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatSchedule(s)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(s.next_run)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(s.last_run)}</TableCell>
                <TableCell>
                  {s.active ? <Badge className="bg-success text-success-foreground">Active</Badge> : <Badge variant="secondary">Inactive</Badge>}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <Button size="icon-sm" variant="ghost" onClick={() => handleRunNow(s)} title="Lancer maintenant">
                      <Play className="size-3.5" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => openEdit(s)}>Modifier</Button>
                    <Button size="icon-sm" variant="ghost" onClick={() => setDeleteTarget(s)}>
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ScheduleFormDialog open={formOpen} onOpenChange={setFormOpen} schedule={activeSchedule} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer cette programmation ?"
        description={deleteTarget ? `La synchronisation automatique de « ${deleteTarget.slug} » sera arrêtée.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteSchedule.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}

const HISTORY_STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  completed: 'default',
  cancelled: 'secondary',
  error: 'destructive',
}

function HistoryTab() {
  const { data: history = [], isLoading } = useSyncHistory()
  const clearHistory = useClearSyncHistory()

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
      <div className="flex justify-end">
        <Button size="sm" variant="destructive" onClick={handleClear} disabled={clearHistory.isPending}>
          <Trash2 className="size-3.5" />
          Vider
        </Button>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Catalogue</TableHead>
              <TableHead>Déclencheur</TableHead>
              <TableHead>Début</TableHead>
              <TableHead>Durée</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Éléments</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}
            {!isLoading && history.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">Aucun historique.</TableCell>
              </TableRow>
            )}
            {history.map((h, i) => (
              <TableRow key={i}>
                <TableCell className="font-medium">{h.slug}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="size-3" />
                    {h.triggered_by}
                  </span>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(h.started_at)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.duration_s}s</TableCell>
                <TableCell>
                  <Badge variant={HISTORY_STATUS_VARIANT[h.status] ?? 'secondary'}>{h.status}</Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{h.total_items ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
