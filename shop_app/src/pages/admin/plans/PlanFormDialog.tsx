import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useCreatePlan, useUpdatePlan, useLibraryFolders } from '@/hooks/useAdminPlans'
import { getApiError } from '@/api/client'
import type { PlanAdmin } from '@/api/types'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'

interface PlanFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  plan: PlanAdmin | null
}

const EMPTY = {
  slug: '', name: '', description: '', price: 0, currency: 'EUR', billing_period: 'month',
  max_devices: 1, allow_downloads: false, is_active: true, sort_order: 0,
}

export function PlanFormDialog({ open, onOpenChange, plan }: PlanFormDialogProps) {
  const { data: folders = [] } = useLibraryFolders()
  const createPlan = useCreatePlan()
  const updatePlan = useUpdatePlan()

  const [form, setForm] = useState(EMPTY)
  const [selectedFolderIds, setSelectedFolderIds] = useState<string[]>([])

  useEffect(() => {
    if (plan) {
      setForm({
        slug: plan.slug, name: plan.name, description: plan.description,
        price: plan.price, currency: plan.currency, billing_period: plan.billing_period,
        max_devices: plan.max_devices, allow_downloads: plan.allow_downloads,
        is_active: plan.is_active, sort_order: plan.sort_order,
      })
      setSelectedFolderIds(plan.jellyfin_library_folder_ids)
    } else {
      setForm(EMPTY)
      setSelectedFolderIds([])
    }
  }, [plan, open])

  function toggleFolder(id: string) {
    setSelectedFolderIds((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]))
  }

  async function handleSubmit() {
    const selectedNames = folders.filter((f) => selectedFolderIds.includes(f.id)).map((f) => f.name)
    const body = {
      ...form,
      jellyfin_library_folder_ids: selectedFolderIds,
      jellyfin_library_names: selectedNames,
    }
    try {
      if (plan) {
        const result = await updatePlan.mutateAsync({ id: plan.id, body })
        if (result.warning) toast.warning(result.warning)
        toast.success('Palier mis à jour')
      } else {
        await createPlan.mutateAsync(body)
        toast.success('Palier créé')
      }
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  const isPending = createPlan.isPending || updatePlan.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{plan ? 'Modifier le palier' : 'Nouveau palier'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="slug">Identifiant (slug)</Label>
              <Input id="slug" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} disabled={!!plan} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="name">Nom</Label>
              <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="price">Prix</Label>
              <Input id="price" type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="currency">Devise</Label>
              <Input id="currency" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max_devices">Appareils</Label>
              <Input id="max_devices" type="number" min={1} value={form.max_devices} onChange={(e) => setForm({ ...form, max_devices: Number(e.target.value) })} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Bibliothèques Jellyfin incluses</Label>
            <div className="flex flex-wrap gap-2">
              {folders.map((f) => (
                <Badge
                  key={f.id}
                  variant={selectedFolderIds.includes(f.id) ? 'default' : 'secondary'}
                  className="cursor-pointer select-none"
                  onClick={() => toggleFolder(f.id)}
                >
                  {f.name}
                </Badge>
              ))}
              {folders.length === 0 && <p className="text-xs text-muted-foreground">Aucune bibliothèque Jellyfin détectée.</p>}
            </div>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <p className="text-sm font-medium">Téléchargement hors ligne</p>
              <p className="text-xs text-muted-foreground">Autorise le téléchargement du contenu depuis les apps Jellyfin.</p>
            </div>
            <Switch checked={form.allow_downloads} onCheckedChange={(v) => setForm({ ...form, allow_downloads: v })} />
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <p className="text-sm font-medium">Palier actif</p>
              <p className="text-xs text-muted-foreground">Visible et souscriptible sur la vitrine.</p>
            </div>
            <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={isPending || !form.slug || !form.name}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            {plan ? 'Enregistrer' : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
