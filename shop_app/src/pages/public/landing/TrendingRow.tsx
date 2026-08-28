const IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'

type ContentKind = 'anime' | 'film' | 'serie'

const KIND_LABEL: Record<ContentKind, string> = {
  anime: 'Anime',
  film: 'Film',
  serie: 'Série',
}

interface TrendingItem {
  title: string
  kind: ContentKind
  poster: string
}

const TRENDING: TrendingItem[] = [
  { title: 'Jujutsu Kaisen', kind: 'anime', poster: '/w2Shg7bI5WB7LINt1KxB7eihO8s.jpg' },
  { title: 'Toy Story 5', kind: 'film', poster: '/b2bt3UomRX41rHHZmIsSNmXzidU.jpg' },
  { title: 'Re:Zero', kind: 'anime', poster: '/ccG0ZfXOQ0834bIus4SwZrXtkyM.jpg' },
  { title: 'Silo', kind: 'serie', poster: '/dxktdopZCOlff10ocoEdn2TXBzl.jpg' },
  { title: 'Bleach', kind: 'anime', poster: '/e0kKmeM8R7Kersh5N2PPzIRNRhr.jpg' },
  { title: 'Vaiana 2', kind: 'film', poster: '/fN4YJFr6d1Zx2fNBlzGLyShO6sc.jpg' },
  { title: 'Mushoku Tensei', kind: 'anime', poster: '/tn2mxPYSSUPHgfcAe5SCga1DO0i.jpg' },
  { title: 'Reacher', kind: 'serie', poster: '/qrJOCIAcvPmyZ63KajWTalQtqPT.jpg' },
  { title: 'Doraemon', kind: 'anime', poster: '/9YqdMXlPTQGLIG67vqZdsPdPC4T.jpg' },
  { title: 'Spider-Man : Brand New Day', kind: 'film', poster: '/yikio8CfJxIA7faZxgvB9FGXy6u.jpg' },
  { title: 'Ted Lasso', kind: 'serie', poster: '/uRHsiw1wLxPHFXkkv4Ix1s0O6f4.jpg' },
]

export function TrendingRow() {
  return (
    <div className="scrollbar-hide flex gap-3 overflow-x-auto pb-2">
      {TRENDING.map((item, i) => (
        <div
          key={item.title}
          className="group relative aspect-2/3 w-32 shrink-0 animate-in fade-in slide-in-from-bottom-4 overflow-hidden rounded-lg bg-muted shadow-sm ring-1 ring-border transition-transform duration-300 ease-out hover:z-10 hover:scale-[1.08] hover:shadow-xl sm:w-40"
          style={{ animationDelay: `${i * 60}ms`, animationDuration: '500ms', animationFillMode: 'backwards' }}
        >
          <img
            src={`${IMAGE_BASE}${item.poster}`}
            alt={item.title}
            loading="lazy"
            className="size-full object-cover"
          />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-2 pt-8">
            <span className="mb-1 inline-block rounded bg-white/15 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
              {KIND_LABEL[item.kind]}
            </span>
            <p className="line-clamp-2 text-xs font-medium text-white">{item.title}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
