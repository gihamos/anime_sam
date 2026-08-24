import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Download,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  Square,
  X,
} from 'lucide-react'
import { useCatalogueContenu, useCatalogues } from '@/hooks/useCatalogues'
import { useDownloadJob } from '@/hooks/useDownloadJob'
import { useSyncSocket } from '@/hooks/useSyncSocket'
import { getApiError } from '@/api/client'
import type { EpisodeContenu, FilmContenu } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface ContentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  slug: string | null
}

export function ContentDialog({ open, onOpenChange, slug }: ContentDialogProps) {
  const { data: contenu, isLoading } = useCatalogueContenu(open ? slug : null)
  const { data: catalogues = [] } = useCatalogues()
  const catalogue = catalogues.find((c) => c.slug === slug)

  const sync = useSyncSocket(slug)
  const dl = useDownloadJob()

  const [seasonIdx, setSeasonIdx] = useState(0)

  useEffect(() => {
    if (open) setSeasonIdx(0)
  }, [open, slug])

  const hasSaisons = (contenu?.saisons.length ?? 0) > 0
  const hasFilms = (contenu?.films.length ?? 0) > 0
  const hasScans = (contenu?.scans.length ?? 0) > 0
  const defaultTab = hasSaisons ? 'saisons' : hasFilms ? 'films' : 'scans'

  const season = contenu?.saisons[seasonIdx]

  async function downloadEpisodes(saisonIdx: number, nums: number[]) {
    if (!slug) return
    try {
      await dl.start({ slug, saison_idx: saisonIdx, nums })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function downloadFilm(filmIdx: number) {
    if (!slug) return
    try {
      await dl.start({ slug, film_idx: filmIdx })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{catalogue?.nom ?? slug}</DialogTitle>
          <DialogDescription>Contenu, synchronisation et téléchargement.</DialogDescription>
        </DialogHeader>

        <SyncBar sync={sync} synced={!!contenu?.episodes_synced} />

        {isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {!isLoading && contenu && !hasSaisons && !hasFilms && !hasScans && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Aucun contenu synchronisé. Lancez une synchronisation pour récupérer les épisodes, films ou chapitres.
          </p>
        )}

        {!isLoading && contenu && (hasSaisons || hasFilms || hasScans) && (
          <Tabs defaultValue={defaultTab}>
            <TabsList>
              {hasSaisons && <TabsTrigger value="saisons">Saisons</TabsTrigger>}
              {hasFilms && <TabsTrigger value="films">Films</TabsTrigger>}
              {hasScans && <TabsTrigger value="scans">Scans</TabsTrigger>}
            </TabsList>

            {hasSaisons && (
              <TabsContent value="saisons" className="space-y-3 pt-2">
                <div className="flex items-center gap-2">
                  <Select value={String(seasonIdx)} onValueChange={(v) => setSeasonIdx(Number(v))}>
                    <SelectTrigger className="flex-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {contenu.saisons.map((s, i) => (
                        <SelectItem key={s.slug} value={String(i)}>{s.nom} ({s.lang})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!!dl.job && dl.job.status !== 'ready' && dl.job.status !== 'error'}
                    onClick={() => downloadEpisodes(seasonIdx, [])}
                  >
                    <Download className="size-3.5" />
                    Toute la saison
                  </Button>
                </div>

                {season && (
                  <ScrollArea className="h-64 rounded-lg border border-border p-2">
                    <div className="grid grid-cols-6 gap-1.5">
                      {season.episodes.map((ep) => (
                        <EpisodeChip
                          key={ep.numero}
                          episode={ep}
                          onDownload={() => downloadEpisodes(seasonIdx, [ep.numero])}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </TabsContent>
            )}

            {hasFilms && (
              <TabsContent value="films" className="space-y-2 pt-2">
                <ScrollArea className="h-64 rounded-lg border border-border">
                  <div className="divide-y divide-border">
                    {contenu.films.map((film, i) => (
                      <FilmRow key={film.slug} film={film} onDownload={() => downloadFilm(i)} />
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}

            {hasScans && (
              <TabsContent value="scans" className="space-y-2 pt-2">
                <ScrollArea className="h-64 rounded-lg border border-border">
                  <div className="divide-y divide-border">
                    {contenu.scans.map((scan) => (
                      <div key={scan.slug} className="flex items-center justify-between px-3 py-2">
                        <span className="text-sm font-medium">{scan.nom}</span>
                        <Badge variant="secondary">{scan.chapitres.length} chapitre(s)</Badge>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            )}
          </Tabs>
        )}

        <DownloadBar job={dl.job} error={dl.error} fileUrl={dl.fileUrl} onCancel={dl.cancel} />
      </DialogContent>
    </Dialog>
  )
}

function EpisodeChip({ episode, onDownload }: { episode: EpisodeContenu; onDownload: () => void }) {
  const videos = episode.videos.filter((v) => v.player_url)
  return (
    <Popover>
      <PopoverTrigger
        render={
          <button className="flex aspect-square items-center justify-center rounded-md border border-border bg-secondary text-xs font-medium transition-colors hover:border-primary/40 hover:bg-primary/10" />
        }
      >
        {episode.numero}
      </PopoverTrigger>
      <PopoverContent>
        <p className="text-sm font-medium">{episode.titre || `Épisode ${episode.numero}`}</p>
        <div className="flex flex-wrap gap-1.5">
          {videos.map((v) => (
            <a
              key={v.lecteur}
              href={v.player_url ?? undefined}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground hover:text-primary"
            >
              {v.lecteur}
              <ExternalLink className="size-3" />
            </a>
          ))}
          {videos.length === 0 && <p className="text-xs text-muted-foreground">Aucun lecteur disponible.</p>}
        </div>
        <Button size="sm" variant="secondary" className="w-full" onClick={onDownload}>
          <Download className="size-3.5" />
          Télécharger
        </Button>
      </PopoverContent>
    </Popover>
  )
}

function FilmRow({ film, onDownload }: { film: FilmContenu; onDownload: () => void }) {
  const videos = film.videos.filter((v) => v.player_url)
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{film.nom}</p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {videos.map((v) => (
            <a
              key={v.lecteur}
              href={v.player_url ?? undefined}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground hover:text-primary"
            >
              {v.lecteur}
              <ExternalLink className="size-3" />
            </a>
          ))}
        </div>
      </div>
      <Button size="sm" variant="secondary" onClick={onDownload}>
        <Download className="size-3.5" />
        Télécharger
      </Button>
    </div>
  )
}

function SyncBar({ sync, synced }: { sync: ReturnType<typeof useSyncSocket>; synced: boolean }) {
  const isRunning = sync.phase === 'running' || sync.phase === 'connecting'
  const lastEvent = sync.log[sync.log.length - 1]

  return (
    <div className="space-y-2 rounded-lg border border-border p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          {isRunning && <Loader2 className="size-3.5 animate-spin text-primary" />}
          Synchronisation
          {!isRunning && synced && <Badge className="bg-success text-success-foreground">Synchronisé</Badge>}
          {!isRunning && !synced && <Badge variant="outline">Non synchronisé</Badge>}
        </div>
        <div className="flex gap-1.5">
          {!isRunning && (
            <Button size="sm" variant="secondary" onClick={sync.start}>
              <RotateCcw className="size-3.5" />
              {synced ? 'Resynchroniser' : 'Synchroniser'}
            </Button>
          )}
          {isRunning && (
            <>
              <Button size="icon-sm" variant="ghost" onClick={sync.pause} title="Pause">
                <Pause className="size-3.5" />
              </Button>
              <Button size="icon-sm" variant="ghost" onClick={sync.resume} title="Reprendre">
                <Play className="size-3.5" />
              </Button>
              <Button size="icon-sm" variant="ghost" onClick={sync.cancel} title="Annuler">
                <Square className="size-3.5" />
              </Button>
            </>
          )}
        </div>
      </div>
      {isRunning && (
        <>
          <Progress value={sync.progress} />
          {lastEvent && (
            <p className="truncate text-xs text-muted-foreground">{describeSyncEvent(lastEvent)}</p>
          )}
        </>
      )}
      {sync.phase === 'error' && sync.errorMessage && (
        <p className="text-xs text-destructive">{sync.errorMessage}</p>
      )}
    </div>
  )
}

function describeSyncEvent(event: { type: string; [key: string]: unknown }): string {
  const nom = typeof event.nom === 'string' ? event.nom : ''
  switch (event.type) {
    case 'saison_start': return `Saison en cours : ${nom}`
    case 'saison_done': return `Saison synchronisée : ${nom}`
    case 'saison_skip': return `Saison déjà à jour : ${nom}`
    case 'film_start': return `Film en cours : ${nom}`
    case 'film_done': return `Film synchronisé : ${nom}`
    case 'scan_start': return `Scan en cours : ${nom}`
    case 'scan_done': return `Scan synchronisé : ${nom}`
    case 'info': return typeof event.message === 'string' ? event.message : ''
    default: return ''
  }
}

function DownloadBar({
  job,
  error,
  fileUrl,
  onCancel,
}: {
  job: ReturnType<typeof useDownloadJob>['job']
  error: string | null
  fileUrl: string | null
  onCancel: () => void
}) {
  if (!job && !error) return null

  return (
    <div className="space-y-1.5 rounded-lg border border-border p-3">
      {error && <p className="text-xs text-destructive">{error}</p>}
      {job && (
        <>
          <div className="flex items-center justify-between text-sm">
            <span className="truncate font-medium">{job.current || job.output_name}</span>
            {job.status !== 'ready' && (
              <Button size="icon-xs" variant="ghost" onClick={onCancel}>
                <X className="size-3.5" />
              </Button>
            )}
          </div>
          {job.status !== 'ready' && job.status !== 'error' && <Progress value={job.progress} />}
          {job.status === 'error' && <p className="text-xs text-destructive">{job.error}</p>}
          {job.status === 'ready' && fileUrl && (
            <a href={fileUrl} className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">
              <Download className="size-3.5" />
              Télécharger {job.output_name}
            </a>
          )}
        </>
      )}
    </div>
  )
}
