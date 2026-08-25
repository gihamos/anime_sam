import { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useGenres } from '@/hooks/useRecherche'
import { useCreateGroup, useUpdateGroup } from '@/hooks/useGroups'
import type { DownloadQuotaConfig, Group, GroupType, QuotaConfig } from '@/api/types'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'

const DEFAULT_QUOTA: QuotaConfig = { enabled: false, period: 'day', max_syncs: 10 }
const DEFAULT_DL_QUOTA: DownloadQuotaConfig = { enabled: false, max_files_per_day: 20, max_gb_per_day: 5 }

interface GroupFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  group: Group | null
}

export function GroupFormDialog({ open, onOpenChange, group }: GroupFormDialogProps) {
  const isEdit = !!group
  const { data: catalogues = [] } = useCatalogues()
  const { data: allGenres = [] } = useGenres()
  const createGroup = useCreateGroup()
  const updateGroup = useUpdateGroup()
  const isPending = createGroup.isPending || updateGroup.isPending

  const [name, setName] = useState('')
  const [type, setType] = useState<GroupType>('catalogue')
  const [description, setDescription] = useState('')
  const [catalogueSlugs, setCatalogueSlugs] = useState<string[]>([])
  const [genres, setGenres] = useState<string[]>([])
  const [cataloguePicker, setCataloguePicker] = useState('')
  const [canSync, setCanSync] = useState(false)
  const [canDelete, setCanDelete] = useState(false)
  const [canRefresh, setCanRefresh] = useState(false)
  const [quota, setQuota] = useState<QuotaConfig>(DEFAULT_QUOTA)
  const [canDownload, setCanDownload] = useState(true)
  const [dlQuota, setDlQuota] = useState<DownloadQuotaConfig>(DEFAULT_DL_QUOTA)

  useEffect(() => {
    if (!open) return
    if (group) {
      setName(group.name)
      setType(group.type)
      setDescription(group.description ?? '')
      setCatalogueSlugs(group.catalogue_slugs)
      setGenres(group.genres)
      setCanSync(group.permissions.can_sync)
      setCanDelete(group.permissions.can_delete)
      setCanRefresh(group.permissions.can_refresh)
      setQuota(group.permissions.quota ?? DEFAULT_QUOTA)
      setCanDownload(group.permissions.can_download)
      setDlQuota({ ...DEFAULT_DL_QUOTA, ...group.permissions.download_quota })
    } else {
      setName('')
      setType('catalogue')
      setDescription('')
      setCatalogueSlugs([])
      setGenres([])
      setCanSync(false)
      setCanDelete(false)
      setCanRefresh(false)
      setQuota(DEFAULT_QUOTA)
      setCanDownload(true)
      setDlQuota(DEFAULT_DL_QUOTA)
    }
    setCataloguePicker('')
  }, [open, group])

  const availableCatalogues = catalogues.filter((c) => !catalogueSlugs.includes(c.slug))
  const visibleGenres = allGenres

  async function handleSave() {
    if (!name.trim()) {
      toast.error('Le nom du groupe est requis')
      return
    }
    const permissions = {
      can_sync: canSync,
      can_delete: canDelete,
      can_refresh: canRefresh,
      can_download: canDownload,
      download_forbidden_slugs: group?.permissions.download_forbidden_slugs ?? [],
      download_quota: dlQuota,
      quota,
    }
    try {
      if (isEdit && group) {
        await updateGroup.mutateAsync({
          id: group.id,
          body: {
            name,
            description,
            catalogue_slugs: catalogueSlugs,
            catalogue_content: group.catalogue_content,
            genres,
            permissions,
          },
        })
        toast.success('Groupe mis à jour')
      } else {
        await createGroup.mutateAsync({
          name,
          type,
          description,
          catalogue_slugs: catalogueSlugs,
          catalogue_content: {},
          genres,
          permissions,
        })
        toast.success('Groupe créé')
      }
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Modifier le groupe' : 'Nouveau groupe'}</DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-[65vh]">
          <div className="space-y-4 pr-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="gf-name">Nom du groupe</Label>
                <Input id="gf-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Abonnés Premium" />
              </div>
              <div className="space-y-1.5">
                <Label>Type</Label>
                <Select value={type} onValueChange={(v) => setType(v as GroupType)} disabled={isEdit}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="catalogue">Catalogues spécifiques</SelectItem>
                    <SelectItem value="genre">Genres de catalogues</SelectItem>
                    <SelectItem value="permission">Permissions seules</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="gf-desc">Description</Label>
              <Input id="gf-desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optionnel" />
            </div>

            {type === 'catalogue' && (
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Catalogues accessibles aux membres
                </Label>
                <Select
                  value={cataloguePicker}
                  onValueChange={(slug) => {
                    if (!slug) return
                    setCatalogueSlugs((prev) => [...prev, String(slug)])
                    setCataloguePicker('')
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Rechercher un catalogue..." />
                  </SelectTrigger>
                  <SelectContent>
                    {availableCatalogues.map((c) => (
                      <SelectItem key={c.slug} value={c.slug}>{c.nom}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="flex flex-wrap gap-1.5">
                  {catalogueSlugs.map((slug) => {
                    const cat = catalogues.find((c) => c.slug === slug)
                    return (
                      <span key={slug} className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                        {cat?.nom ?? slug}
                        <button type="button" onClick={() => setCatalogueSlugs((prev) => prev.filter((s) => s !== slug))}>
                          <X className="size-3" />
                        </button>
                      </span>
                    )
                  })}
                  {catalogueSlugs.length === 0 && <p className="text-xs text-muted-foreground">Aucun catalogue sélectionné.</p>}
                </div>
              </div>
            )}

            {type === 'genre' && (
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Genres — accès à tous les catalogues correspondants
                </Label>
                <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-border p-2">
                  {visibleGenres.map((g) => {
                    const active = genres.includes(g)
                    return (
                      <button
                        key={g}
                        type="button"
                        onClick={() => setGenres((prev) => (active ? prev.filter((x) => x !== g) : [...prev, g]))}
                        className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${active ? 'border-primary/40 bg-primary/15 text-primary' : 'border-border bg-secondary text-secondary-foreground'}`}
                      >
                        {g}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            <div className="space-y-2 rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Permissions accordées aux membres</p>
              <PermissionRow label="Synchroniser" checked={canSync} onChange={setCanSync} />
              <PermissionRow label="Supprimer" checked={canDelete} onChange={setCanDelete} />
              <PermissionRow label="Rafraîchir" checked={canRefresh} onChange={setCanRefresh} />
              <div className="flex items-center justify-between pt-1">
                <Label className="font-normal">Quota de synchronisation</Label>
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

            <div className="space-y-2 rounded-lg border border-border p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Téléchargements</p>
              <PermissionRow label="Autoriser le téléchargement" checked={canDownload} onChange={setCanDownload} />
              <div className="flex items-center justify-between pt-1">
                <Label className="font-normal">Quota de téléchargement</Label>
                <Switch checked={!!dlQuota.enabled} onCheckedChange={(v) => setDlQuota({ ...dlQuota, enabled: v })} />
              </div>
              {dlQuota.enabled && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Fichiers / jour</Label>
                    <Input type="number" min={1} value={dlQuota.max_files_per_day} onChange={(e) => setDlQuota({ ...dlQuota, max_files_per_day: Number(e.target.value) })} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Go / jour</Label>
                    <Input type="number" min={0.1} step={0.5} value={dlQuota.max_gb_per_day} onChange={(e) => setDlQuota({ ...dlQuota, max_gb_per_day: Number(e.target.value) })} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>

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
