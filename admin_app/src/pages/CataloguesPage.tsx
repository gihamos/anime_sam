import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import {
  Eye,
  EyeOff,
  FolderOpen,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import {
  useBulkDeleteCatalogues,
  useBulkRefreshCatalogues,
  useBulkUpdateVisibility,
  useCatalogues,
  useDeleteCatalogue,
  useRefreshCatalogue,
} from '@/hooks/useCatalogues'
import { getApiError } from '@/api/client'
import type { CatalogueAdminSummary, Etat, Source, TypeContenu } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { AddCatalogueDialog } from './catalogues/AddCatalogueDialog'
import { EditMetaDialog } from './catalogues/EditMetaDialog'
import { VisibilityDialog } from './catalogues/VisibilityDialog'
import { ContentDialog } from './catalogues/ContentDialog'

type Filter = string | 'all'
type DialogKind = 'add' | 'edit' | 'visibility' | 'content' | null

const TYPE_LABELS: Record<TypeContenu, string> = {
  anime: 'Anime',
  scan: 'Scan',
  film: 'Film',
  serie: 'Série',
  autre: 'Autre',
}

const ETAT_LABELS: Record<Etat, string> = {
  en_cours: 'En cours',
  termine: 'Terminé',
  abandonne: 'Abandonné',
}

const SOURCE_LABELS: Record<Source, string> = {
  'anime-sama': 'anime-sama.to',
  'tmdb-vidzy': 'TMDB',
}

export function CataloguesPage() {
  const { data: catalogues = [], isLoading } = useCatalogues()
  const deleteCatalogue = useDeleteCatalogue()
  const refreshCatalogue = useRefreshCatalogue()
  const bulkDelete = useBulkDeleteCatalogues()
  const bulkRefresh = useBulkRefreshCatalogues()
  const bulkVisibility = useBulkUpdateVisibility()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<Filter>('all')
  const [sourceFilter, setSourceFilter] = useState<Filter>('all')
  const [visibilityFilter, setVisibilityFilter] = useState<Filter>('all')
  const [etatFilter, setEtatFilter] = useState<Filter>('all')
  const [syncFilter, setSyncFilter] = useState<Filter>('all')
  const [genreFilter, setGenreFilter] = useState<Filter>('all')

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [dialog, setDialog] = useState<DialogKind>(null)
  const [activeSlug, setActiveSlug] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CatalogueAdminSummary | null>(null)
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)

  const genres = useMemo(() => {
    const set = new Set<string>()
    catalogues.forEach((c) => c.genres.forEach((g) => set.add(g)))
    return Array.from(set).sort()
  }, [catalogues])

  const filtered = catalogues.filter((c) => {
    if (search && !c.nom.toLowerCase().includes(search.toLowerCase())) return false
    if (typeFilter !== 'all' && c.type_contenu !== typeFilter) return false
    if (sourceFilter !== 'all' && (c.source ?? 'anime-sama') !== sourceFilter) return false
    if (visibilityFilter === 'public' && !c.visibility.is_public) return false
    if (visibilityFilter === 'private' && c.visibility.is_public) return false
    if (etatFilter !== 'all' && c.etat !== etatFilter) return false
    if (syncFilter === 'synced' && !c.episodes_synced) return false
    if (syncFilter === 'unsynced' && c.episodes_synced) return false
    if (genreFilter !== 'all' && !c.genres.includes(genreFilter)) return false
    return true
  })

  function toggleSelect(slug: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(slug)) next.delete(slug)
      else next.add(slug)
      return next
    })
  }

  function toggleSelectAll() {
    setSelected((prev) => (prev.size === filtered.length ? new Set() : new Set(filtered.map((c) => c.slug))))
  }

  function openDialog(kind: DialogKind, slug: string | null) {
    setActiveSlug(slug)
    setDialog(kind)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteCatalogue.mutateAsync(deleteTarget.slug)
      toast.success('Catalogue supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleRefresh(slug: string) {
    try {
      await refreshCatalogue.mutateAsync(slug)
      toast.success('Catalogue rafraîchi')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleBulkDelete() {
    try {
      const res = await bulkDelete.mutateAsync(Array.from(selected))
      toast.success(`${res.ok.length} catalogue(s) supprimé(s)`)
      if (Object.keys(res.errors).length > 0) toast.error(`${Object.keys(res.errors).length} erreur(s)`)
      setSelected(new Set())
      setBulkDeleteConfirm(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleBulkRefresh() {
    try {
      const res = await bulkRefresh.mutateAsync(Array.from(selected))
      toast.success(`${res.ok.length} catalogue(s) rafraîchi(s)`)
      if (Object.keys(res.errors).length > 0) toast.error(`${Object.keys(res.errors).length} erreur(s)`)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleBulkVisibility(isPublic: boolean) {
    try {
      await bulkVisibility.mutateAsync({ slugs: Array.from(selected), isPublic })
      toast.success('Visibilité mise à jour')
      setSelected(new Set())
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Catalogues</h1>
          <p className="text-sm text-muted-foreground">Animes, films, séries et scans du catalogue.</p>
        </div>
        <Button onClick={() => openDialog('add', null)}>
          <Plus className="size-4" />
          Ajouter
        </Button>
      </div>

      <div className="space-y-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un titre..."
            className="pl-8"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterSelect value={typeFilter} onChange={setTypeFilter} placeholder="Type" options={[
            ...Object.entries(TYPE_LABELS).map(([value, label]) => ({ value, label })),
          ]} />
          <FilterSelect value={sourceFilter} onChange={setSourceFilter} placeholder="Source" options={[
            ...Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label })),
          ]} />
          <FilterSelect value={visibilityFilter} onChange={setVisibilityFilter} placeholder="Visibilité" options={[
            { value: 'public', label: 'Public' },
            { value: 'private', label: 'Privé' },
          ]} />
          <FilterSelect value={etatFilter} onChange={setEtatFilter} placeholder="État" options={[
            ...Object.entries(ETAT_LABELS).map(([value, label]) => ({ value, label })),
          ]} />
          <FilterSelect value={syncFilter} onChange={setSyncFilter} placeholder="Synchronisation" options={[
            { value: 'synced', label: 'Synchronisé' },
            { value: 'unsynced', label: 'Non synchronisé' },
          ]} />
          <FilterSelect value={genreFilter} onChange={setGenreFilter} placeholder="Genre" options={genres.map((g) => ({ value: g, label: g }))} />
        </div>
      </div>

      {selected.size > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5">
          <p className="text-sm font-medium">{selected.size} sélectionné(s)</p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleBulkRefresh} disabled={bulkRefresh.isPending}>
              {bulkRefresh.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
              Rafraîchir
            </Button>
            <Button size="sm" variant="outline" onClick={() => handleBulkVisibility(true)} disabled={bulkVisibility.isPending}>
              <Eye className="size-3.5" />
              Rendre public
            </Button>
            <Button size="sm" variant="outline" onClick={() => handleBulkVisibility(false)} disabled={bulkVisibility.isPending}>
              <EyeOff className="size-3.5" />
              Rendre privé
            </Button>
            <Button size="sm" variant="destructive" onClick={() => setBulkDeleteConfirm(true)}>
              <Trash2 className="size-3.5" />
              Supprimer
            </Button>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={filtered.length > 0 && selected.size === filtered.length}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>Nom</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>État</TableHead>
              <TableHead>Visibilité</TableHead>
              <TableHead>Sync</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={8}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun catalogue trouvé.
                </TableCell>
              </TableRow>
            )}

            {filtered.map((cat) => (
              <TableRow key={cat.slug}>
                <TableCell>
                  <Checkbox checked={selected.has(cat.slug)} onCheckedChange={() => toggleSelect(cat.slug)} />
                </TableCell>
                <TableCell>
                  <button className="text-left font-medium hover:text-primary" onClick={() => openDialog('content', cat.slug)}>
                    {cat.nom}
                  </button>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{TYPE_LABELS[cat.type_contenu]}</Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{SOURCE_LABELS[cat.source ?? 'anime-sama']}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{ETAT_LABELS[cat.etat]}</TableCell>
                <TableCell>
                  {cat.visibility.is_public ? (
                    <Badge className="bg-success text-success-foreground">Public</Badge>
                  ) : (
                    <Badge variant="secondary">Privé</Badge>
                  )}
                </TableCell>
                <TableCell>
                  {cat.episodes_synced ? (
                    <Badge className="bg-info text-info-foreground">Synchronisé</Badge>
                  ) : (
                    <Badge variant="outline">Non synchronisé</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openDialog('content', cat.slug)}>
                        <FolderOpen className="size-4" />
                        Contenu
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('edit', cat.slug)}>
                        <Pencil className="size-4" />
                        Modifier
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('visibility', cat.slug)}>
                        <Eye className="size-4" />
                        Visibilité
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleRefresh(cat.slug)}>
                        <RefreshCw className="size-4" />
                        Rafraîchir
                      </DropdownMenuItem>
                      <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(cat)}>
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

      <AddCatalogueDialog open={dialog === 'add'} onOpenChange={(v) => setDialog(v ? 'add' : null)} />
      <EditMetaDialog open={dialog === 'edit'} onOpenChange={(v) => setDialog(v ? 'edit' : null)} slug={activeSlug} />
      <VisibilityDialog open={dialog === 'visibility'} onOpenChange={(v) => setDialog(v ? 'visibility' : null)} slug={activeSlug} />
      <ContentDialog open={dialog === 'content'} onOpenChange={(v) => setDialog(v ? 'content' : null)} slug={activeSlug} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer ce catalogue ?"
        description={deleteTarget ? `« ${deleteTarget.nom} » et tout son contenu seront définitivement supprimés.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteCatalogue.isPending}
        onConfirm={handleDelete}
      />

      <ConfirmDialog
        open={bulkDeleteConfirm}
        onOpenChange={setBulkDeleteConfirm}
        title={`Supprimer ${selected.size} catalogue(s) ?`}
        description="Cette action est irréversible."
        confirmLabel="Supprimer"
        destructive
        isPending={bulkDelete.isPending}
        onConfirm={handleBulkDelete}
      />
    </div>
  )
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  options: { value: string; label: string }[]
}) {
  return (
    <Select value={value} onValueChange={(v) => v && onChange(v)}>
      <SelectTrigger className="w-40">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{placeholder} — Tous</SelectItem>
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
