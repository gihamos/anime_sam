import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogueDetail, useUpdateCatalogueMeta } from '@/hooks/useCatalogues'
import type { Etat, TypeContenu } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { TagInput } from '@/components/shared/TagInput'

interface EditMetaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  slug: string | null
}

export function EditMetaDialog({ open, onOpenChange, slug }: EditMetaDialogProps) {
  const { data: detail, isLoading } = useCatalogueDetail(open ? slug : null)
  const updateMeta = useUpdateCatalogueMeta()

  const [nom, setNom] = useState('')
  const [titreAlt, setTitreAlt] = useState('')
  const [synopsis, setSynopsis] = useState('')
  const [etat, setEtat] = useState<Etat>('en_cours')
  const [type, setType] = useState<TypeContenu>('anime')
  const [genres, setGenres] = useState<string[]>([])
  const [langues, setLangues] = useState<string[]>([])

  useEffect(() => {
    if (!detail) return
    setNom(detail.nom)
    setTitreAlt(detail.titre_alternatif ?? '')
    setSynopsis(detail.synopsis ?? '')
    setEtat(detail.etat)
    setType(detail.type_contenu)
    setGenres(detail.genres)
    setLangues(detail.langues)
  }, [detail])

  async function handleSave() {
    if (!slug) return
    try {
      await updateMeta.mutateAsync({
        slug,
        body: {
          nom,
          titre_alternatif: titreAlt,
          synopsis,
          etat,
          type_contenu: type,
          genres,
          langues,
        },
      })
      toast.success('Métadonnées mises à jour')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Modifier le catalogue</DialogTitle>
          <DialogDescription>{slug}</DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        )}

        {!isLoading && detail && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="em-nom">Nom</Label>
                <Input id="em-nom" value={nom} onChange={(e) => setNom(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="em-alt">Titre alternatif</Label>
                <Input id="em-alt" value={titreAlt} onChange={(e) => setTitreAlt(e.target.value)} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="em-synopsis">Synopsis</Label>
              <Textarea id="em-synopsis" value={synopsis} onChange={(e) => setSynopsis(e.target.value)} rows={4} />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Type</Label>
                <Select value={type} onValueChange={(v) => setType(v as TypeContenu)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="anime">Anime</SelectItem>
                    <SelectItem value="scan">Scan</SelectItem>
                    <SelectItem value="film">Film</SelectItem>
                    <SelectItem value="serie">Série</SelectItem>
                    <SelectItem value="autre">Autre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>État</Label>
                <Select value={etat} onValueChange={(v) => setEtat(v as Etat)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en_cours">En cours</SelectItem>
                    <SelectItem value="termine">Terminé</SelectItem>
                    <SelectItem value="abandonne">Abandonné</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Genres</Label>
              <TagInput value={genres} onChange={setGenres} placeholder="Ajouter un genre..." />
            </div>

            <div className="space-y-1.5">
              <Label>Langues</Label>
              <TagInput value={langues} onChange={setLangues} placeholder="Ajouter une langue..." />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateMeta.isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={updateMeta.isPending || isLoading}>
            {updateMeta.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
