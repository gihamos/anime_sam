import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2, MoreHorizontal, Search } from 'lucide-react'
import { useAdminSubscriptions, useExtendSubscription, useForceCancelSubscription } from '@/hooks/useAdminSubscriptions'
import { useAdminPlans } from '@/hooks/useAdminPlans'
import { getApiError } from '@/api/client'
import type { SubscriptionAdmin } from '@/api/types'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'

const STATUS_OPTIONS = ['all', 'pending', 'active', 'past_due', 'suspended', 'cancelled', 'expired']

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function SubscriptionsAdminPage() {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)
  const [status, setStatus] = useState('all')
  const { data: plans = [] } = useAdminPlans()

  const { data: subscriptions = [], isLoading } = useAdminSubscriptions({
    status: status === 'all' ? undefined : status,
    search: debouncedSearch || undefined,
  })

  const extend = useExtendSubscription()
  const forceCancel = useForceCancelSubscription()

  const [extendTarget, setExtendTarget] = useState<SubscriptionAdmin | null>(null)
  const [extendDays, setExtendDays] = useState(30)
  const [cancelTarget, setCancelTarget] = useState<SubscriptionAdmin | null>(null)

  const planNameById = Object.fromEntries(plans.map((p) => [p.id, p.name]))

  async function handleExtend() {
    if (!extendTarget) return
    try {
      await extend.mutateAsync({ id: extendTarget.id, days: extendDays })
      toast.success('Abonnement prolongé')
      setExtendTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleForceCancel() {
    if (!cancelTarget) return
    try {
      await forceCancel.mutateAsync({ id: cancelTarget.id })
      toast.success('Abonnement annulé et accès désactivé')
      setCancelTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Abonnements</h1>
        <p className="text-sm text-muted-foreground">Suivi et gestion des abonnements clients.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un client..." className="pl-8" />
        </div>
        <Select value={status} onValueChange={(v) => setStatus(v ?? 'all')}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>{s === 'all' ? 'Tous statuts' : s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Client</TableHead>
              <TableHead>Palier</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Fin de période</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}

            {!isLoading && subscriptions.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun abonnement.
                </TableCell>
              </TableRow>
            )}

            {subscriptions.map((sub) => (
              <TableRow key={sub.id}>
                <TableCell className="font-medium">{sub.username}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{planNameById[sub.plan_id] ?? sub.plan_id}</TableCell>
                <TableCell>
                  <Badge variant={sub.status === 'active' ? 'default' : 'secondary'}>{sub.status}</Badge>
                  {sub.cancel_at_period_end && <Badge variant="secondary" className="ml-1.5">fin de période</Badge>}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(sub.current_period_end)}</TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => { setExtendTarget(sub); setExtendDays(30) }}>
                        Prolonger
                      </DropdownMenuItem>
                      <DropdownMenuItem variant="destructive" onClick={() => setCancelTarget(sub)}>
                        Annuler maintenant
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!extendTarget} onOpenChange={(v) => !v && setExtendTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Prolonger l'abonnement</DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="days">Nombre de jours</Label>
            <Input id="days" type="number" min={1} value={extendDays} onChange={(e) => setExtendDays(Number(e.target.value))} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExtendTarget(null)}>Annuler</Button>
            <Button onClick={handleExtend} disabled={extend.isPending}>
              {extend.isPending && <Loader2 className="size-4 animate-spin" />}
              Prolonger
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!cancelTarget}
        onOpenChange={(v) => !v && setCancelTarget(null)}
        title="Annuler cet abonnement ?"
        description={cancelTarget ? `L'accès Jellyfin de « ${cancelTarget.username} » sera désactivé immédiatement.` : undefined}
        confirmLabel="Annuler l'abonnement"
        destructive
        isPending={forceCancel.isPending}
        onConfirm={handleForceCancel}
      />
    </div>
  )
}
