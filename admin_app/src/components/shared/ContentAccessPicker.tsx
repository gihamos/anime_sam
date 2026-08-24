import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ContentAccess } from '@/api/types'

interface Item {
  slug: string
  label: string
}

interface ContentAccessPickerProps {
  saisons: Item[]
  films: Item[]
  scans: Item[]
  value: ContentAccess
  onChange: (value: ContentAccess) => void
}

function Section({
  title,
  items,
  selected,
  onChange,
}: {
  title: string
  items: Item[]
  selected: string[]
  onChange: (next: string[]) => void
}) {
  if (items.length === 0) return null
  const isAll = selected.length === 0

  function toggle(slug: string) {
    if (isAll) {
      onChange([slug])
      return
    }
    const next = selected.includes(slug) ? selected.filter((s) => s !== slug) : [...selected, slug]
    onChange(next)
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        <Pill active={isAll} onClick={() => onChange([])}>
          Tous
        </Pill>
        {items.map((item) => (
          <Pill key={item.slug} active={!isAll && selected.includes(item.slug)} onClick={() => toggle(item.slug)}>
            {item.label}
          </Pill>
        ))}
      </div>
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

/** Choix fin des saisons/films/scans d'UN catalogue — liste vide = tout est inclus. */
export function ContentAccessPicker({ saisons, films, scans, value, onChange }: ContentAccessPickerProps) {
  return (
    <div className="space-y-3 rounded-md border border-border bg-muted/40 p-3">
      <Section
        title="Saisons"
        items={saisons}
        selected={value.saisons}
        onChange={(next) => onChange({ ...value, saisons: next })}
      />
      <Section
        title="Films"
        items={films}
        selected={value.films}
        onChange={(next) => onChange({ ...value, films: next })}
      />
      <Section
        title="Scans"
        items={scans}
        selected={value.scans}
        onChange={(next) => onChange({ ...value, scans: next })}
      />
      {saisons.length === 0 && films.length === 0 && scans.length === 0 && (
        <p className="text-xs text-muted-foreground">Aucun contenu synchronisé pour ce catalogue.</p>
      )}
    </div>
  )
}
