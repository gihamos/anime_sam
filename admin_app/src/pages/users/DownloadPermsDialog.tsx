import { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useUpdateDownloadPerms } from '@/hooks/useUsers'
import type { User } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface DownloadPermsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
}

export function DownloadPermsDialog({ open, onOpenChange, user }: DownloadPermsDialogProps) {
  const { data: catalogues = [] } = useCatalogues()
  const updatePerms = useUpdateDownloadPerms()

  const [canDownload, setCanDownload] = useState(true)
  const [forbidden, setForbidden] = useState<string[]>([])
  const [pickerValue, setPickerValue] = useState('')

  useEffect(() => {
    if (!open || !user) return
    setCanDownload(user.permissions.can_download)
    setForbidden(user.permissions.download_forbidden_slugs ?? [])
    setPickerValue('')
  }, [open, user])

  const available = catalogues.filter((c) => !forbidden.includes(c.slug))

  async function handleSave() {
    if (!user) return
    try {
      await updatePerms.mutateAsync({ username: user.username, canDownload, forbiddenSlugs: forbidden })
      toast.success('Permissions de téléchargement mises à jour')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Téléchargement</DialogTitle>
          <DialogDescription>Compte « {user?.username} »</DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
          <Label htmlFor="dl-enabled" className="font-normal">Téléchargement autorisé</Label>
          <Switch id="dl-enabled" checked={canDownload} onCheckedChange={setCanDownload} />
        </div>

        {canDownload && (
          <div className="space-y-2">
            <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Catalogues interdits au téléchargement
            </Label>
            <Select value={pickerValue} onValueChange={(slug) => {
              if (!slug) return
              setForbidden((prev) => [...prev, String(slug)])
              setPickerValue('')
            }}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Ajouter un catalogue..." />
              </SelectTrigger>
              <SelectContent>
                {available.map((c) => (
                  <SelectItem key={c.slug} value={c.slug}>{c.nom}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex flex-wrap gap-1.5">
              {forbidden.map((slug) => {
                const cat = catalogues.find((c) => c.slug === slug)
                return (
                  <span
                    key={slug}
                    className="inline-flex items-center gap-1 rounded-md bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive"
                  >
                    {cat?.nom ?? slug}
                    <button type="button" onClick={() => setForbidden((prev) => prev.filter((s) => s !== slug))}>
                      <X className="size-3" />
                    </button>
                  </span>
                )
              })}
              {forbidden.length === 0 && (
                <p className="text-xs text-muted-foreground">Aucune restriction — tout est téléchargeable.</p>
              )}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updatePerms.isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={updatePerms.isPending}>
            {updatePerms.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
