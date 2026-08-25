import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useUpdateApiClient } from '@/hooks/useApiClients'
import type { ApiClient, ContentAccess } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ContentAccessPicker } from '@/components/shared/ContentAccessPicker'

const EMPTY_CONTENT: ContentAccess = { saisons: [], films: [], scans: [] }

interface ClientAccessDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  client: ApiClient | null
}

export function ClientAccessDialog({ open, onOpenChange, client }: ClientAccessDialogProps) {
  const { data: catalogues = [] } = useCatalogues()
  const updateClient = useUpdateApiClient()

  const [allAccess, setAllAccess] = useState(true)
  const [selected, setSelected] = useState<string[]>([])
  const [content, setContent] = useState<Record<string, ContentAccess>>({})
  const [expanded, setExpanded] = useState<string | null>(null)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    if (!open || !client) return
    const allowed = client.permissions.allowed_catalogues
    setAllAccess(allowed.length === 0)
    setSelected(allowed)
    setContent(client.permissions.catalogue_content ?? {})
    setExpanded(null)
    setFilter('')
  }, [open, client])

  function toggleCatalogue(slug: string) {
    setSelected((prev) => (prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]))
  }

  async function handleSave() {
    if (!client) return
    try {
      await updateClient.mutateAsync({
        clientId: client.client_id,
        body: {
          permissions: {
            ...client.permissions,
            allowed_catalogues: allAccess ? [] : selected,
            catalogue_content: allAccess ? {} : content,
          },
        },
      })
      toast.success('Accès mis à jour')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  const filtered = catalogues.filter((c) => c.nom.toLowerCase().includes(filter.toLowerCase()))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Accès aux catalogues</DialogTitle>
          <DialogDescription>Application « {client?.name} »</DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
          <Label htmlFor="ca-all" className="font-normal">Accès à tous les catalogues</Label>
          <Switch id="ca-all" checked={allAccess} onCheckedChange={setAllAccess} />
        </div>

        {!allAccess && (
          <>
            <Input placeholder="Filtrer les catalogues..." value={filter} onChange={(e) => setFilter(e.target.value)} />
            <ScrollArea className="h-72 rounded-lg border border-border">
              <div className="divide-y divide-border">
                {filtered.map((cat) => {
                  const isSelected = selected.includes(cat.slug)
                  const isExpanded = expanded === cat.slug
                  return (
                    <div key={cat.slug}>
                      <div className="flex items-center gap-2 px-3 py-2">
                        <Checkbox checked={isSelected} onCheckedChange={() => toggleCatalogue(cat.slug)} />
                        <button
                          type="button"
                          className="flex flex-1 items-center justify-between gap-2 text-left text-sm"
                          onClick={() => isSelected && setExpanded(isExpanded ? null : cat.slug)}
                        >
                          <span className="truncate">{cat.nom}</span>
                          {isSelected && (isExpanded ? <ChevronDown className="size-4 shrink-0 text-muted-foreground" /> : <ChevronRight className="size-4 shrink-0 text-muted-foreground" />)}
                        </button>
                      </div>
                      {isSelected && isExpanded && (
                        <div className="px-3 pb-3">
                          <ContentAccessPicker
                            saisons={cat.saisons.map((s) => ({ slug: s.slug, label: s.nom }))}
                            films={cat.films.map((f) => ({ slug: f.slug, label: f.nom }))}
                            scans={cat.scans.map((s) => ({ slug: s.slug, label: s.nom }))}
                            value={content[cat.slug] ?? EMPTY_CONTENT}
                            onChange={(next) => setContent((prev) => ({ ...prev, [cat.slug]: next }))}
                          />
                        </div>
                      )}
                    </div>
                  )
                })}
                {filtered.length === 0 && (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">Aucun catalogue.</p>
                )}
              </div>
            </ScrollArea>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateClient.isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={updateClient.isPending}>
            {updateClient.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
