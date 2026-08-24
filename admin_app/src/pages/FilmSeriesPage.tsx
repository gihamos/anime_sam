import { useState } from 'react'
import { toast } from 'sonner'
import { Check, Clapperboard, Film, Loader2, Search, Star, Tv } from 'lucide-react'
import { useAddFromTmdb, useTmdbSearch } from '@/hooks/useFilmSeries'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { getApiError } from '@/api/client'
import type { TmdbMediaType, TmdbSearchResult } from '@/api/types'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

type TypeFilter = TmdbMediaType | 'all'

export function FilmSeriesPage() {
  const [query, setQuery] = useState('')
  const [type, setType] = useState<TypeFilter>('all')
  const debouncedQuery = useDebouncedValue(query, 400)

  const search = useTmdbSearch(debouncedQuery, type)
  const addFromTmdb = useAddFromTmdb()

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
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Films et séries</h1>
        <p className="text-sm text-muted-foreground">
          Recherche TMDB, ajout au catalogue avec lecteur Vidzy.
        </p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher un titre..."
            className="pl-8"
            autoFocus
          />
        </div>
        <Select value={type} onValueChange={(v) => setType(v as TypeFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous types</SelectItem>
            <SelectItem value="movie">Films</SelectItem>
            <SelectItem value="tv">Séries</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {query.trim().length > 0 && query.trim().length < 2 && (
        <p className="text-sm text-muted-foreground">Continuez à taper pour lancer la recherche.</p>
      )}

      {search.isLoading && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="aspect-[2/3] rounded-lg" />
          ))}
        </div>
      )}

      {search.isError && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-16 text-center">
          <Clapperboard className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{getApiError(search.error)}</p>
        </div>
      )}

      {search.data && search.data.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {search.data.map((result) => (
            <ResultCard
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
      )}

      {!search.isLoading && !search.isError && debouncedQuery.trim().length >= 2 && search.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">Aucun résultat pour « {debouncedQuery} ».</p>
      )}

      {debouncedQuery.trim().length < 2 && !search.isLoading && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground">
          <Search className="size-8" />
          <p className="text-sm">Cherchez un film ou une série à ajouter au catalogue.</p>
        </div>
      )}
    </div>
  )
}

function ResultCard({
  result,
  onAdd,
  isAdding,
}: {
  result: TmdbSearchResult
  onAdd: () => void
  isAdding: boolean
}) {
  return (
    <div className="group flex flex-col overflow-hidden rounded-lg bg-card ring-1 ring-foreground/10">
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
