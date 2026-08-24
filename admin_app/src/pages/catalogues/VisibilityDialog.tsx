import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues, useUpdateCatalogueVisibility } from '@/hooks/useCatalogues'
import type { ContentAccess } from '@/api/types'
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
import { ContentAccessPicker } from '@/components/shared/ContentAccessPicker'

interface VisibilityDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  slug: string | null
}

export function VisibilityDialog({ open, onOpenChange, slug }: VisibilityDialogProps) {
  const { data: catalogues = [] } = useCatalogues()
  const updateVisibility = useUpdateCatalogueVisibility()
  const catalogue = catalogues.find((c) => c.slug === slug) ?? null

  const [isPublic, setIsPublic] = useState(false)
  const [content, setContent] = useState<ContentAccess>({ saisons: [], films: [], scans: [] })

  useEffect(() => {
    if (!open || !catalogue) return
    setIsPublic(catalogue.visibility.is_public)
    setContent({
      saisons: catalogue.visibility.public_saisons,
      films: catalogue.visibility.public_films,
      scans: catalogue.visibility.public_scans,
    })
  }, [open, catalogue])

  async function handleSave() {
    if (!slug) return
    try {
      await updateVisibility.mutateAsync({
        slug,
        body: {
          is_public: isPublic,
          public_saisons: content.saisons,
          public_films: content.films,
          public_scans: content.scans,
        },
      })
      toast.success('Visibilité mise à jour')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Visibilité publique</DialogTitle>
          <DialogDescription>{catalogue?.nom}</DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
          <Label htmlFor="vis-public" className="font-normal">Visible publiquement (sans compte)</Label>
          <Switch id="vis-public" checked={isPublic} onCheckedChange={setIsPublic} />
        </div>

        {isPublic && catalogue && (
          <ContentAccessPicker
            saisons={catalogue.saisons.map((s) => ({ slug: s.slug, label: s.nom }))}
            films={catalogue.films.map((f) => ({ slug: f.slug, label: f.nom }))}
            scans={catalogue.scans.map((s) => ({ slug: s.slug, label: s.nom }))}
            value={content}
            onChange={setContent}
          />
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateVisibility.isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={updateVisibility.isPending}>
            {updateVisibility.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
