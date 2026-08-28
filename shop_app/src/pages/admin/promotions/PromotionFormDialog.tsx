import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useCreatePromotion, useUpdatePromotion } from '@/hooks/useAdminPromotions'
import { useAdminPlans } from '@/hooks/useAdminPlans'
import { getApiError } from '@/api/client'
import type { DiscountType, Promotion } from '@/api/types'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

interface PromotionFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  promotion: Promotion | null
}

const EMPTY = {
  code: '', description: '', discount_type: 'percent' as DiscountType, discount_value: 10,
  max_uses: null as number | null, expires_at: null as string | null, is_active: true,
}

export function PromotionFormDialog({ open, onOpenChange, promotion }: PromotionFormDialogProps) {
  const { data: plans = [] } = useAdminPlans()
  const createPromotion = useCreatePromotion()
  const updatePromotion = useUpdatePromotion()

  const [form, setForm] = useState(EMPTY)
  const [selectedPlanIds, setSelectedPlanIds] = useState<string[]>([])

  useEffect(() => {
    if (promotion) {
      setForm({
        code: promotion.code, description: promotion.description,
        discount_type: promotion.discount_type, discount_value: promotion.discount_value,
        max_uses: promotion.max_uses, expires_at: promotion.expires_at?.slice(0, 10) ?? null,
        is_active: promotion.is_active,
      })
      setSelectedPlanIds(promotion.applicable_plan_ids)
    } else {
      setForm(EMPTY)
      setSelectedPlanIds([])
    }
  }, [promotion, open])

  function togglePlan(id: string) {
    setSelectedPlanIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]))
  }

  async function handleSubmit() {
    const body = {
      ...form,
      code: form.code.trim().toUpperCase(),
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      applicable_plan_ids: selectedPlanIds,
    }
    try {
      if (promotion) {
        await updatePromotion.mutateAsync({ id: promotion.id, body })
        toast.success('Code promo mis à jour')
      } else {
        await createPromotion.mutateAsync(body)
        toast.success('Code promo créé')
      }
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  const isPending = createPromotion.isPending || updatePromotion.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{promotion ? 'Modifier le code promo' : 'Nouveau code promo'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="code">Code</Label>
            <Input
              id="code"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              placeholder="BIENVENUE20"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Réservé aux nouveaux clients, offre de bienvenue"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Type de remise</Label>
              <Select
                value={form.discount_type}
                onValueChange={(v) => setForm({ ...form, discount_type: v as DiscountType })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="percent">Pourcentage</SelectItem>
                  <SelectItem value="fixed">Montant fixe</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="discount_value">
                Valeur {form.discount_type === 'percent' ? '(%)' : '(montant)'}
              </Label>
              <Input
                id="discount_value"
                type="number"
                step="0.01"
                min={0}
                value={form.discount_value}
                onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="max_uses">Utilisations maximum</Label>
              <Input
                id="max_uses"
                type="number"
                min={1}
                placeholder="Illimité"
                value={form.max_uses ?? ''}
                onChange={(e) => setForm({ ...form, max_uses: e.target.value ? Number(e.target.value) : null })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="expires_at">Expire le</Label>
              <Input
                id="expires_at"
                type="date"
                value={form.expires_at ?? ''}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value || null })}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Paliers concernés</Label>
            <div className="flex flex-wrap gap-2">
              {plans.map((p) => (
                <Badge
                  key={p.id}
                  variant={selectedPlanIds.includes(p.id) ? 'default' : 'secondary'}
                  className="cursor-pointer select-none"
                  onClick={() => togglePlan(p.id)}
                >
                  {p.name}
                </Badge>
              ))}
              {plans.length === 0 && <p className="text-xs text-muted-foreground">Aucun palier créé.</p>}
            </div>
            <p className="text-xs text-muted-foreground">Aucune sélection : le code s'applique à tous les paliers.</p>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <p className="text-sm font-medium">Code actif</p>
              <p className="text-xs text-muted-foreground">Utilisable immédiatement par les clients.</p>
            </div>
            <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={isPending || !form.code || form.discount_value <= 0}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            {promotion ? 'Enregistrer' : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
