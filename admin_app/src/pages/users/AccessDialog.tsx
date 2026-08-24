import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useUpdateUser } from '@/hooks/useUsers'
import type { ContentAccess, User } from '@/api/types'
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

interface AccessDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
}

export function AccessDialog({ open, onOpenChange, user }: AccessDialogProps) {
  const { data: catalogues = [] } = useCatalogues()
  const updateUser = useUpdateUser()

  const [allAccess, setAllAccess] = useState(true)
  const [selected, setSelected] = useState<string[]>([])
  const [content, setContent] = useState<Record<string, ContentAccess>>({})
  const [expanded, setExpanded] = useState<string | null>(null)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    if (!open || !user) return
    const allowed = user.permissions.allowed_catalogues
    setAllAccess(allowed.length === 0)
    setSelected(allowed)
    setContent(user.permissions.catalogue_content ?? {})
    setExpanded(null)
    setFilter('')
  }, [open, user])

  function toggleCatalogue(slug: string) {
    setSelected((prev) => (prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]))
  }

  async function handleSave() {
    if (!user) return
    try {
      await updateUser.mutateAsync({
        username: user.username,
        body: {
          permissions: {
            ...user.permissions,
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
          <DialogDescription>Compte « {user?.username} »</DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
          <Label htmlFor="acc-all" className="font-normal">Accès à tous les catalogues</Label>
          <Switch id="acc-all" checked={allAccess} onCheckedChange={setAllAccess} />
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
            <p className="text-xs text-muted-foreground">{selected.length} catalogue(s) sélectionné(s)</p>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateUser.isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={updateUser.isPending}>
            {updateUser.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
