import { useState } from 'react'
import { toast } from 'sonner'
import { MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import { useAdminPromotions, useDeletePromotion } from '@/hooks/useAdminPromotions'
import { getApiError } from '@/api/client'
import type { Promotion } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { PromotionFormDialog } from './promotions/PromotionFormDialog'

function formatDiscount(promo: Promotion) {
  return promo.discount_type === 'percent'
    ? `-${promo.discount_value}%`
    : `-${promo.discount_value.toFixed(2)}`
}

export function PromotionsAdminPage() {
  const { data: promotions = [], isLoading } = useAdminPromotions()
  const deletePromotion = useDeletePromotion()

  const [formOpen, setFormOpen] = useState(false)
  const [activePromo, setActivePromo] = useState<Promotion | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Promotion | null>(null)

  function openForm(promo: Promotion | null) {
    setActivePromo(promo)
    setFormOpen(true)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deletePromotion.mutateAsync(deleteTarget.id)
      toast.success('Code promo supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Promotions</h1>
          <p className="text-sm text-muted-foreground">Codes de réduction pour animer les ventes et récompenser vos clients.</p>
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
              <TableHead>Code</TableHead>
              <TableHead>Remise</TableHead>
              <TableHead>Utilisation</TableHead>
              <TableHead>Expire le</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}

            {!isLoading && promotions.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun code promo créé.
                </TableCell>
              </TableRow>
            )}

            {promotions.map((promo) => (
              <TableRow key={promo.id}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{promo.code}</span>
                    {promo.description && <span className="text-xs text-muted-foreground">{promo.description}</span>}
                  </div>
                </TableCell>
                <TableCell>{formatDiscount(promo)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {promo.used_count}{promo.max_uses !== null ? ` / ${promo.max_uses}` : ''}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {promo.expires_at ? new Date(promo.expires_at).toLocaleDateString('fr-FR') : 'Jamais'}
                </TableCell>
                <TableCell>
                  <Badge variant={promo.is_active ? 'default' : 'secondary'}>{promo.is_active ? 'Actif' : 'Inactif'}</Badge>
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openForm(promo)}>Modifier</DropdownMenuItem>
                      <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(promo)}>
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

      <PromotionFormDialog open={formOpen} onOpenChange={setFormOpen} promotion={activePromo} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer ce code promo ?"
        description={deleteTarget ? `« ${deleteTarget.code} » sera supprimé définitivement.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deletePromotion.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
