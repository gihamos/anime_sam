import { useState } from 'react'
import { toast } from 'sonner'
import { Check, Loader2, Search } from 'lucide-react'
import { useAddCatalogueByUrl, useSiteSearch } from '@/hooks/useCatalogues'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { getApiError } from '@/api/client'
import type { SiteSearchResult } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface AddCatalogueDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddCatalogueDialog({ open, onOpenChange }: AddCatalogueDialogProps) {
  const [query, setQuery] = useState('')
  const [manual, setManual] = useState('')
  const [addingSlug, setAddingSlug] = useState<string | null>(null)
  const debouncedQuery = useDebouncedValue(query, 400)

  const search = useSiteSearch(debouncedQuery)
  const addByUrl = useAddCatalogueByUrl()

  async function handleAdd(result: SiteSearchResult) {
    setAddingSlug(result.slug)
    try {
      await addByUrl.mutateAsync(result.slug)
      toast.success(`« ${result.nom} » ajouté au catalogue`)
    } catch (err) {
      toast.error(getApiError(err))
    } finally {
      setAddingSlug(null)
    }
  }

  async function handleManualAdd() {
    if (!manual.trim()) return
    try {
      await addByUrl.mutateAsync(manual.trim())
      toast.success('Catalogue ajouté')
      setManual('')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ajouter un catalogue</DialogTitle>
          <DialogDescription>Depuis anime-sama.to — recherche ou slug/URL direct.</DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="search">
          <TabsList className="w-full">
            <TabsTrigger value="search" className="flex-1">Recherche</TabsTrigger>
            <TabsTrigger value="manual" className="flex-1">Slug ou URL</TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="space-y-3 pt-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Rechercher un titre..."
                className="pl-8"
                autoFocus
              />
            </div>

            {search.isLoading && (
              <div className="flex justify-center py-8">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            )}

            {search.isError && (
              <p className="py-6 text-center text-sm text-muted-foreground">{getApiError(search.error)}</p>
            )}

            {search.data && search.data.length > 0 && (
              <ScrollArea className="h-72 rounded-lg border border-border">
                <div className="divide-y divide-border">
                  {search.data.map((result) => (
                    <div key={result.slug} className="flex items-center gap-3 p-2.5">
                      {result.image ? (
                        <img src={result.image} alt={result.nom} className="size-12 shrink-0 rounded object-cover" />
                      ) : (
                        <div className="size-12 shrink-0 rounded bg-muted" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{result.nom}</p>
                        <p className="truncate text-xs text-muted-foreground">{result.genres.join(', ')}</p>
                      </div>
                      <Button size="sm" variant="secondary" disabled={addingSlug === result.slug} onClick={() => handleAdd(result)}>
                        {addingSlug === result.slug ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
                        Ajouter
                      </Button>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            {debouncedQuery.trim().length < 2 && (
              <p className="py-6 text-center text-sm text-muted-foreground">Tapez au moins 2 caractères.</p>
            )}
          </TabsContent>

          <TabsContent value="manual" className="space-y-3 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="manual-slug">Slug ou URL anime-sama.to</Label>
              <Input
                id="manual-slug"
                value={manual}
                onChange={(e) => setManual(e.target.value)}
                placeholder="https://anime-sama.fr/catalogue/... ou slug"
              />
            </div>
            <Button className="w-full" disabled={!manual.trim() || addByUrl.isPending} onClick={handleManualAdd}>
              {addByUrl.isPending && <Loader2 className="size-4 animate-spin" />}
              Ajouter
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
