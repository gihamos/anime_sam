import { useEffect, useState } from 'react'
import { Loader2, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useDeleteDlQuota, useSetDlQuota } from '@/hooks/useDownloadsAdmin'
import type { DlQuota } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface DlQuotaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  username: string | null
  quota: DlQuota | null
}

export function DlQuotaDialog({ open, onOpenChange, username, quota }: DlQuotaDialogProps) {
  const setQuota = useSetDlQuota()
  const deleteQuota = useDeleteDlQuota()

  const [maxFiles, setMaxFiles] = useState(20)
  const [maxGb, setMaxGb] = useState(10)
  const [canDownload, setCanDownload] = useState(true)

  useEffect(() => {
    if (!open) return
    setMaxFiles(quota?.max_files_per_day ?? 20)
    setMaxGb(quota?.max_gb_per_day ?? 10)
    setCanDownload(quota?.can_download ?? true)
  }, [open, quota])

  async function handleSave() {
    if (!username) return
    try {
      await setQuota.mutateAsync({ username, maxFilesPerDay: maxFiles, maxGbPerDay: maxGb, canDownload })
      toast.success('Quota enregistré')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleDelete() {
    if (!username) return
    try {
      await deleteQuota.mutateAsync(username)
      toast.success('Quota supprimé — retour au défaut')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Quota — {username}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Fichiers maximum / 24h</Label>
            <Input type="number" min={0} value={maxFiles} onChange={(e) => setMaxFiles(Number(e.target.value))} />
          </div>
          <div className="space-y-1.5">
            <Label>Go maximum / 24h</Label>
            <Input type="number" min={0} step={0.5} value={maxGb} onChange={(e) => setMaxGb(Number(e.target.value))} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
            <Label className="font-normal">Téléchargement autorisé</Label>
            <Switch checked={canDownload} onCheckedChange={setCanDownload} />
          </div>
        </div>

        <DialogFooter className="sm:justify-between">
          {quota && (
            <Button variant="destructive" onClick={handleDelete} disabled={deleteQuota.isPending} className="sm:mr-auto">
              {deleteQuota.isPending ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
              Supprimer
            </Button>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={setQuota.isPending}>
              Annuler
            </Button>
            <Button onClick={handleSave} disabled={setQuota.isPending}>
              {setQuota.isPending && <Loader2 className="size-4 animate-spin" />}
              Enregistrer
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
