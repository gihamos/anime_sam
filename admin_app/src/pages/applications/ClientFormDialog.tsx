import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCreateApiClient, useUpdateApiClient } from '@/hooks/useApiClients'
import type { ApiClient, QuotaConfig } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const DEFAULT_QUOTA: QuotaConfig = { enabled: false, period: 'month', max_syncs: 10 }

interface ClientFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  client: ApiClient | null
  onCreated: (client: ApiClient & { client_secret: string }) => void
}

export function ClientFormDialog({ open, onOpenChange, client, onCreated }: ClientFormDialogProps) {
  const isEdit = !!client
  const createClient = useCreateApiClient()
  const updateClient = useUpdateApiClient()
  const isPending = createClient.isPending || updateClient.isPending

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [canSync, setCanSync] = useState(false)
  const [canDelete, setCanDelete] = useState(false)
  const [canRefresh, setCanRefresh] = useState(false)
  const [quota, setQuota] = useState<QuotaConfig>(DEFAULT_QUOTA)

  useEffect(() => {
    if (!open) return
    if (client) {
      setName(client.name)
      setDescription(client.description ?? '')
      setIsActive(client.is_active)
      setCanSync(client.permissions.can_sync)
      setCanDelete(client.permissions.can_delete)
      setCanRefresh(client.permissions.can_refresh)
      setQuota(client.permissions.quota ?? DEFAULT_QUOTA)
    } else {
      setName('')
      setDescription('')
      setIsActive(true)
      setCanSync(false)
      setCanDelete(false)
      setCanRefresh(false)
      setQuota(DEFAULT_QUOTA)
    }
  }, [open, client])

  async function handleSave() {
    if (!name.trim()) {
      toast.error("Le nom de l'application est requis")
      return
    }
    try {
      if (isEdit && client) {
        await updateClient.mutateAsync({
          clientId: client.client_id,
          body: {
            name,
            description,
            is_active: isActive,
            permissions: {
              ...client.permissions,
              can_sync: canSync,
              can_delete: canDelete,
              can_refresh: canRefresh,
              quota,
            },
          },
        })
        toast.success('Application mise à jour')
        onOpenChange(false)
      } else {
        const created = await createClient.mutateAsync({
          name,
          description,
          permissions: {
            can_sync: canSync,
            can_delete: canDelete,
            can_refresh: canRefresh,
            allowed_catalogues: [],
            catalogue_content: {},
            quota,
          },
        })
        onOpenChange(false)
        onCreated(created)
      }
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Modifier l'application" : 'Nouvelle application'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="cf-name">Nom de l'application</Label>
            <Input id="cf-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Mon application" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cf-desc">Description</Label>
            <Textarea id="cf-desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Usage de l'application" rows={2} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
            <Label htmlFor="cf-active" className="font-normal">Application active</Label>
            <Switch id="cf-active" checked={isActive} onCheckedChange={setIsActive} />
          </div>

          <div className="space-y-2 rounded-lg border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Permissions</p>
            <PermissionRow label="Synchronisation" checked={canSync} onChange={setCanSync} />
            <PermissionRow label="Suppression" checked={canDelete} onChange={setCanDelete} />
            <PermissionRow label="Rafraîchissement" checked={canRefresh} onChange={setCanRefresh} />
          </div>

          <div className="space-y-2 rounded-lg border border-border p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quota de synchronisation</p>
              <Switch checked={quota.enabled} onCheckedChange={(v) => setQuota({ ...quota, enabled: v })} />
            </div>
            {quota.enabled && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Input type="number" min={1} value={quota.max_syncs} onChange={(e) => setQuota({ ...quota, max_syncs: Number(e.target.value) })} />
                <Select value={quota.period} onValueChange={(v) => setQuota({ ...quota, period: v as QuotaConfig['period'] })}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="day">Par jour</SelectItem>
                    <SelectItem value="month">Par mois</SelectItem>
                    <SelectItem value="year">Par an</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PermissionRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <Label className="font-normal">{label}</Label>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  )
}
