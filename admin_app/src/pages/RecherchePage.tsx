import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Check, Clapperboard, Film, Loader2, Search, Star, Tv, X } from 'lucide-react'
import { useAddCatalogueByUrl, useCatalogues } from '@/hooks/useCatalogues'
import { useGenres, useSiteSearchAdvanced, type SiteSearchFilters } from '@/hooks/useRecherche'
import { useAddFromTmdb, useTmdbGenres, useTmdbSearch, type TmdbSearchFilters } from '@/hooks/useFilmSeries'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { getApiError } from '@/api/client'
import type { SiteSearchResult, TmdbMediaType, TmdbSearchResult } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

const TYPES = ['Anime', 'Scans', 'Film', 'Autres']
const LANGUES = ['VOSTFR', 'VF', 'VASTFR']
const STATUTS = ['En cours', 'Terminé']

// Pays d'origine courants pour filtrer les films/séries TMDB (ex : dramas coréens, tokusatsu
// japonais, séries turques) — code ISO 3166-1, envoyé tel quel à `with_origin_country` côté
// TMDB. Liste volontairement restreinte aux origines les plus demandées plutôt que la liste
// complète des ~250 pays TMDB (peu utile ici et jamais localisée en français par leur API).
const TMDB_COUNTRIES: { code: string; label: string }[] = [
  { code: 'KR', label: 'Corée du Sud' },
  { code: 'JP', label: 'Japon' },
  { code: 'CN', label: 'Chine' },
  { code: 'TW', label: 'Taïwan' },
  { code: 'HK', label: 'Hong Kong' },
  { code: 'TH', label: 'Thaïlande' },
  { code: 'IN', label: 'Inde' },
  { code: 'TR', label: 'Turquie' },
  { code: 'FR', label: 'France' },
  { code: 'GB', label: 'Royaume-Uni' },
  { code: 'US', label: 'États-Unis' },
  { code: 'ES', label: 'Espagne' },
  { code: 'DE', label: 'Allemagne' },
  { code: 'IT', label: 'Italie' },
  { code: 'BR', label: 'Brésil' },
  { code: 'MX', label: 'Mexique' },
  { code: 'CA', label: 'Canada' },
]

const EMPTY_FILTERS: SiteSearchFilters = {
  search: '',
  types: [],
  langues: [],
  statuts: [],
  genres: [],
  anneeMin: '',
  anneeMax: '',
  page: 1,
}

export function RecherchePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Recherche</h1>
        <p className="text-sm text-muted-foreground">Trouvez du contenu à ajouter au catalogue, par source.</p>
      </div>

      <Tabs defaultValue="anime-sama">
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="anime-sama">anime-sama.to</TabsTrigger>
            <TabsTrigger value="tmdb">TMDB (films et séries)</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="anime-sama" className="pt-4">
          <AnimeSamaSearch />
        </TabsContent>
        <TabsContent value="tmdb" className="pt-4">
          <TmdbSearch />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Pill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-primary/40 bg-primary/15 text-primary'
          : 'border-border bg-secondary text-secondary-foreground hover:border-primary/30',
      )}
    >
      {active && <Check className="size-3" />}
      {children}
    </button>
  )
}

function AnimeSamaSearch() {
  const [filters, setFilters] = useState<SiteSearchFilters>(EMPTY_FILTERS)
  const [genreFilter, setGenreFilter] = useState('')
  const [addingSlug, setAddingSlug] = useState<string | null>(null)

  const { data: catalogues = [] } = useCatalogues()
  const { data: allGenres = [] } = useGenres()
  const search = useSiteSearchAdvanced(filters)
  const addByUrl = useAddCatalogueByUrl()

  const knownSlugs = useMemo(() => new Set(catalogues.map((c) => c.slug)), [catalogues])
  const visibleGenres = allGenres.filter((g) => g.toLowerCase().includes(genreFilter.toLowerCase()))

  function toggleIn(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
  }

  function runSearch(page: number) {
    setFilters({ ...filters, page })
  }

  const wasFetched = search.isFetched
  const resetKey = JSON.stringify({ ...filters, page: undefined })
  const list = useAccumulatedResults(search.data, filters.page, resetKey)

  function resetFilters() {
    setFilters(EMPTY_FILTERS)
    setGenreFilter('')
  }

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

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Titre</label>
          <Input
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            placeholder="Naruto, One Piece..."
            onKeyDown={(e) => e.key === 'Enter' && runSearch(1)}
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type</label>
          <div className="flex flex-wrap gap-1.5">
            {TYPES.map((t) => (
              <Pill key={t} active={filters.types.includes(t)} onClick={() => setFilters({ ...filters, types: toggleIn(filters.types, t) })}>
                {t}
              </Pill>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Langue</label>
          <div className="flex flex-wrap gap-1.5">
            {LANGUES.map((l) => (
              <Pill key={l} active={filters.langues.includes(l)} onClick={() => setFilters({ ...filters, langues: toggleIn(filters.langues, l) })}>
                {l}
              </Pill>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Statut</label>
          <div className="flex flex-wrap gap-1.5">
            {STATUTS.map((s) => (
              <Pill key={s} active={filters.statuts.includes(s)} onClick={() => setFilters({ ...filters, statuts: toggleIn(filters.statuts, s) })}>
                {s}
              </Pill>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Année</label>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              placeholder="1990"
              value={filters.anneeMin}
              onChange={(e) => setFilters({ ...filters, anneeMin: e.target.value })}
            />
            <span className="text-muted-foreground">–</span>
            <Input
              type="number"
              placeholder="2026"
              value={filters.anneeMax}
              onChange={(e) => setFilters({ ...filters, anneeMax: e.target.value })}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Genres {filters.genres.length > 0 && <span className="text-primary">({filters.genres.length})</span>}
          </label>
          <Input value={genreFilter} onChange={(e) => setGenreFilter(e.target.value)} placeholder="Filtrer les genres..." />
          <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-border p-2">
            {visibleGenres.map((g) => (
              <Pill key={g} active={filters.genres.includes(g)} onClick={() => setFilters({ ...filters, genres: toggleIn(filters.genres, g) })}>
                {g}
              </Pill>
            ))}
            {visibleGenres.length === 0 && <p className="text-xs text-muted-foreground">Aucun genre.</p>}
          </div>
        </div>

        <div className="flex gap-2">
          <Button className="flex-1" onClick={() => runSearch(1)} disabled={search.isFetching}>
            {search.isFetching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
            Rechercher
          </Button>
          <Button variant="ghost" size="icon" onClick={resetFilters} title="Réinitialiser">
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {!wasFetched && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground">
            <Search className="size-8" />
            <p className="text-sm">Utilisez les filtres pour rechercher des catalogues sur anime-sama.to.</p>
          </div>
        )}

        {search.isFetching && filters.page === 1 && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[2/3] rounded-lg" />
            ))}
          </div>
        )}

        {wasFetched && !search.isFetching && list.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">Aucun résultat pour ces critères.</p>
        )}

        {list.length > 0 && (
          <>
            <p className="text-xs text-muted-foreground">{list.length} résultat(s)</p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {list.map((r) => (
                <SiteResultCard
                  key={r.slug}
                  result={r}
                  inDb={knownSlugs.has(r.slug ?? '')}
                  isAdding={addingSlug === r.slug}
                  onAdd={() => handleAdd(r)}
                />
              ))}
            </div>
            {list.length >= 18 * filters.page && (
              <div className="flex justify-center pt-2">
                <Button variant="secondary" onClick={() => runSearch(filters.page + 1)} disabled={search.isFetching}>
                  {search.isFetching && <Loader2 className="size-4 animate-spin" />}
                  Charger plus
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// Le résultat courant de la query ne contient que la page en cours — on accumule
// les pages précédentes ici pour le "Charger plus" (comportement de l'ancienne interface).
// `resetKey` identifie les filtres hors pagination : s'il change, on repart de zéro
// même si `page` reste à 1 (sinon une nouvelle recherche sur la page 1 n'afficherait
// pas ses résultats tant que la page elle-même n'a pas changé).
function useAccumulatedResults<T>(pageData: T[] | undefined, page: number, resetKey: string): T[] {
  const [acc, setAcc] = useState<{ resetKey: string; page: number; items: T[] }>({
    resetKey: '',
    page: 0,
    items: [],
  })

  if (pageData && (resetKey !== acc.resetKey || page !== acc.page)) {
    const items = page === 1 || resetKey !== acc.resetKey ? pageData : [...acc.items, ...pageData]
    setAcc({ resetKey, page, items })
    return items
  }
  return acc.items
}

function SiteResultCard({
  result,
  inDb,
  isAdding,
  onAdd,
}: {
  result: SiteSearchResult
  inDb: boolean
  isAdding: boolean
  onAdd: () => void
}) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg bg-card ring-1 ring-foreground/10">
      <div className="relative aspect-[2/3] bg-muted">
        {result.image ? (
          <img src={result.image} alt={result.nom} className="size-full object-cover" loading="lazy" />
        ) : (
          <div className="flex size-full items-center justify-center text-muted-foreground">
            <Clapperboard className="size-8" />
          </div>
        )}
        {inDb && (
          <Badge className="absolute right-1.5 top-1.5 gap-1 bg-success text-success-foreground">
            <Check className="size-3" />
            En base
          </Badge>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-2.5">
        <p className="line-clamp-2 text-sm font-medium leading-snug">{result.nom}</p>
        <div className="flex flex-wrap gap-1 text-xs text-muted-foreground">
          {result.genres.slice(0, 2).map((g) => (
            <span key={g}>{g}</span>
          ))}
        </div>
        <Button
          size="sm"
          variant={inDb ? 'secondary' : 'default'}
          className="mt-auto w-full"
          disabled={inDb || isAdding}
          onClick={onAdd}
        >
          {isAdding && <Loader2 className="size-3.5 animate-spin" />}
          {inDb ? 'Déjà ajouté' : 'Ajouter'}
        </Button>
      </div>
    </div>
  )
}

const EMPTY_TMDB_FILTERS: TmdbSearchFilters = {
  query: '',
  mediaType: 'all',
  genreIds: [],
  anneeMin: '',
  anneeMax: '',
  pays: '',
  page: 1,
}

function TmdbSearch() {
  const [filters, setFilters] = useState<TmdbSearchFilters>(EMPTY_TMDB_FILTERS)
  const [genreFilter, setGenreFilter] = useState('')
  const debouncedQuery = useDebouncedValue(filters.query, 400)
  const debouncedFilters = useMemo(() => ({ ...filters, query: debouncedQuery, page: filters.page }), [filters, debouncedQuery])

  const { data: genresData } = useTmdbGenres()
  const search = useTmdbSearch(debouncedFilters)
  const addFromTmdb = useAddFromTmdb()

  const availableGenres = useMemo(() => {
    if (!genresData) return []
    const list = filters.mediaType === 'all'
      ? [...genresData.movie, ...genresData.tv].filter((g, i, arr) => arr.findIndex((x) => x.id === g.id) === i)
      : genresData[filters.mediaType]
    return list.filter((g) => g.name.toLowerCase().includes(genreFilter.toLowerCase()))
  }, [genresData, filters.mediaType, genreFilter])

  function toggleGenre(id: number) {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      genreIds: prev.genreIds.includes(id) ? prev.genreIds.filter((g) => g !== id) : [...prev.genreIds, id],
    }))
  }

  function resetFilters() {
    setFilters(EMPTY_TMDB_FILTERS)
    setGenreFilter('')
  }

  const wasFetched = search.isFetched
  const resetKey = JSON.stringify({ ...debouncedFilters, page: undefined })
  const list = useAccumulatedResults(search.data, debouncedFilters.page, resetKey)

  function handleAdd(result: TmdbSearchResult) {
    addFromTmdb.mutate(
      { mediaType: result.media_type, tmdbId: result.tmdb_id },
      {
        onSuccess: () => toast.success(`« ${result.nom} » ajouté au catalogue`),
        onError: (err) => toast.error(getApiError(err)),
      },
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Titre</label>
          <Input
            value={filters.query}
            onChange={(e) => setFilters({ ...filters, query: e.target.value, page: 1 })}
            placeholder="Inception, The Office..."
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type</label>
          <Select value={filters.mediaType} onValueChange={(v) => setFilters({ ...filters, mediaType: (v as TmdbMediaType | 'all') ?? 'all', page: 1 })}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous types</SelectItem>
              <SelectItem value="movie">Films</SelectItem>
              <SelectItem value="tv">Séries</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Année de sortie</label>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              placeholder="1990"
              value={filters.anneeMin}
              onChange={(e) => setFilters({ ...filters, anneeMin: e.target.value, page: 1 })}
            />
            <span className="text-muted-foreground">–</span>
            <Input
              type="number"
              placeholder="2026"
              value={filters.anneeMax}
              onChange={(e) => setFilters({ ...filters, anneeMax: e.target.value, page: 1 })}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Genres {filters.genreIds.length > 0 && <span className="text-primary">({filters.genreIds.length})</span>}
          </label>
          <Input value={genreFilter} onChange={(e) => setGenreFilter(e.target.value)} placeholder="Filtrer les genres..." />
          <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-border p-2">
            {availableGenres.map((g) => (
              <Pill key={g.id} active={filters.genreIds.includes(g.id)} onClick={() => toggleGenre(g.id)}>
                {g.name}
              </Pill>
            ))}
            {availableGenres.length === 0 && <p className="text-xs text-muted-foreground">Aucun genre.</p>}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pays d'origine</label>
          <div className="flex flex-wrap gap-1.5">
            {TMDB_COUNTRIES.map((c) => (
              <Pill
                key={c.code}
                active={filters.pays === c.code}
                onClick={() => setFilters({ ...filters, pays: filters.pays === c.code ? '' : c.code, page: 1 })}
              >
                {c.label}
              </Pill>
            ))}
          </div>
        </div>

        <Button variant="ghost" className="w-full" onClick={resetFilters}>
          <X className="size-4" />
          Réinitialiser
        </Button>
      </div>

      <div className="space-y-3">
        {filters.query.trim().length === 1 && (
          <p className="text-sm text-muted-foreground">Continuez à taper pour lancer la recherche.</p>
        )}

        {!wasFetched && filters.query.trim().length !== 1 && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground">
            <Search className="size-8" />
            <p className="text-sm">Cherchez un titre ou parcourez par genre/année.</p>
          </div>
        )}

        {search.isFetching && filters.page === 1 && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[2/3] rounded-lg" />
            ))}
          </div>
        )}

        {search.isError && <p className="py-8 text-center text-sm text-muted-foreground">{getApiError(search.error)}</p>}

        {list.length > 0 && (
          <>
            <p className="text-xs text-muted-foreground">{list.length} résultat(s)</p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {list.map((result) => (
                <TmdbResultCard
                  key={`${result.media_type}-${result.tmdb_id}`}
                  result={result}
                  onAdd={() => handleAdd(result)}
                  isAdding={
                    addFromTmdb.isPending &&
                    addFromTmdb.variables?.tmdbId === result.tmdb_id &&
                    addFromTmdb.variables?.mediaType === result.media_type
                  }
                />
              ))}
            </div>
            {list.length >= 20 * filters.page && (
              <div className="flex justify-center pt-2">
                <Button variant="secondary" onClick={() => setFilters({ ...filters, page: filters.page + 1 })} disabled={search.isFetching}>
                  {search.isFetching && <Loader2 className="size-4 animate-spin" />}
                  Charger plus
                </Button>
              </div>
            )}
          </>
        )}

        {wasFetched && !search.isFetching && !search.isError && list.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">Aucun résultat pour ces critères.</p>
        )}
      </div>
    </div>
  )
}

function TmdbResultCard({
  result,
  onAdd,
  isAdding,
}: {
  result: TmdbSearchResult
  onAdd: () => void
  isAdding: boolean
}) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg bg-card ring-1 ring-foreground/10">
      <div className="relative aspect-[2/3] bg-muted">
        {result.image ? (
          <img src={result.image} alt={result.nom} className="size-full object-cover" loading="lazy" />
        ) : (
          <div className="flex size-full items-center justify-center text-muted-foreground">
            {result.media_type === 'movie' ? <Film className="size-8" /> : <Tv className="size-8" />}
          </div>
        )}
        <Badge variant="secondary" className="absolute left-1.5 top-1.5">
          {result.media_type === 'movie' ? 'Film' : 'Série'}
        </Badge>
        {result.in_db && (
          <Badge className="absolute right-1.5 top-1.5 gap-1 bg-success text-success-foreground">
            <Check className="size-3" />
            En base
          </Badge>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-2.5">
        <p className="line-clamp-2 text-sm font-medium leading-snug">{result.nom}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {result.annee && <span>{result.annee}</span>}
          {result.note !== null && (
            <span className="flex items-center gap-0.5">
              <Star className="size-3 fill-warning text-warning" />
              {result.note.toFixed(1)}
            </span>
          )}
        </div>
        <Button
          size="sm"
          variant={result.in_db ? 'secondary' : 'default'}
          className="mt-auto w-full"
          disabled={result.in_db || isAdding}
          onClick={onAdd}
        >
          {isAdding && <Loader2 className="size-3.5 animate-spin" />}
          {result.in_db ? 'Déjà ajouté' : 'Ajouter'}
        </Button>
      </div>
    </div>
  )
}
