import { useState } from 'react'
import { toast } from 'sonner'
import { MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import { useAdminPlans, useDeletePlan } from '@/hooks/useAdminPlans'
import { getApiError } from '@/api/client'
import type { PlanAdmin } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { PlanFormDialog } from './plans/PlanFormDialog'

function activeDiscount(plan: PlanAdmin): string | null {
  if (!plan.discount_type || plan.discount_value === null) return null
  if (plan.discount_expires_at && plan.discount_expires_at < new Date().toISOString()) return null
  return plan.discount_type === 'percent' ? `-${plan.discount_value}%` : `-${plan.discount_value.toFixed(2)} ${plan.currency}`
}

export function PlansAdminPage() {
  const { data: plans = [], isLoading } = useAdminPlans()
  const deletePlan = useDeletePlan()

  const [formOpen, setFormOpen] = useState(false)
  const [activePlan, setActivePlan] = useState<PlanAdmin | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<PlanAdmin | null>(null)

  function openForm(plan: PlanAdmin | null) {
    setActivePlan(plan)
    setFormOpen(true)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deletePlan.mutateAsync(deleteTarget.id)
      toast.success('Palier supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Offres</h1>
          <p className="text-sm text-muted-foreground">Paliers d'abonnement proposés sur la vitrine.</p>
        </div>
        <Button onClick={() => openForm(null)}>
          <Plus className="size-4" />
          Ajouter
        </Button>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>Prix</TableHead>
              <TableHead>Bibliothèques</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}

            {!isLoading && plans.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun palier créé.
                </TableCell>
              </TableRow>
            )}

            {plans.map((plan) => (
              <TableRow key={plan.id}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{plan.name}</span>
                    <span className="text-xs text-muted-foreground">{plan.slug}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{plan.price.toFixed(2)} {plan.currency} / {plan.duration_days} j</span>
                    {activeDiscount(plan) && <Badge variant="default">{activeDiscount(plan)}</Badge>}
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span>{plan.jellyfin_library_names.length > 0 ? plan.jellyfin_library_names.join(', ') : '—'}</span>
                    {plan.max_parental_rating !== null && (
                      <Badge variant="secondary">
                        {plan.max_parental_rating === 0 ? 'Tous publics' : `-${plan.max_parental_rating}`}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={plan.is_active ? 'default' : 'secondary'}>{plan.is_active ? 'Actif' : 'Inactif'}</Badge>
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openForm(plan)}>Modifier</DropdownMenuItem>
                      <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(plan)}>
                        <Trash2 className="size-4" />
                        Supprimer
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <PlanFormDialog open={formOpen} onOpenChange={setFormOpen} plan={activePlan} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer ce palier ?"
        description={deleteTarget ? `« ${deleteTarget.name} » sera supprimé définitivement.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deletePlan.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
