import { useMemo, useState } from 'react'
import type { DailyRevenuePoint } from '@/api/types'

interface RevenueChartProps {
  data: DailyRevenuePoint[]
  currency: string
}

const WIDTH = 720
const HEIGHT = 220
const PAD_X = 12
const PAD_TOP = 16
const PAD_BOTTOM = 28

export function RevenueChart({ data, currency }: RevenueChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  const { path, areaPath, points, maxAmount } = useMemo(() => {
    const max = Math.max(1, ...data.map((d) => d.amount))
    const innerWidth = WIDTH - PAD_X * 2
    const innerHeight = HEIGHT - PAD_TOP - PAD_BOTTOM
    const step = data.length > 1 ? innerWidth / (data.length - 1) : 0

    const pts = data.map((d, i) => ({
      x: PAD_X + step * i,
      y: PAD_TOP + innerHeight - (d.amount / max) * innerHeight,
      ...d,
    }))

    const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')
    const area = pts.length > 0
      ? `${linePath} L ${pts[pts.length - 1].x.toFixed(2)} ${HEIGHT - PAD_BOTTOM} L ${pts[0].x.toFixed(2)} ${HEIGHT - PAD_BOTTOM} Z`
      : ''

    return { path: linePath, areaPath: area, points: pts, maxAmount: max }
  }, [data])

  const hovered = hoverIndex !== null ? points[hoverIndex] : null

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    const idx = Math.round(ratio * (points.length - 1))
    setHoverIndex(Math.min(Math.max(idx, 0), points.length - 1))
  }

  if (data.length === 0) {
    return <p className="py-16 text-center text-sm text-muted-foreground">Aucune vente enregistrée pour le moment.</p>
  }

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <line
          x1={PAD_X} y1={HEIGHT - PAD_BOTTOM} x2={WIDTH - PAD_X} y2={HEIGHT - PAD_BOTTOM}
          stroke="var(--color-border)" strokeWidth={1}
        />
        <path d={areaPath} fill="var(--color-primary)" opacity={0.08} />
        <path d={path} fill="none" stroke="var(--color-primary)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

        {hovered && (
          <g>
            <line
              x1={hovered.x} y1={PAD_TOP} x2={hovered.x} y2={HEIGHT - PAD_BOTTOM}
              stroke="var(--color-border)" strokeWidth={1} strokeDasharray="3 3"
            />
            <circle cx={hovered.x} cy={hovered.y} r={4} fill="var(--color-primary)" stroke="var(--color-card)" strokeWidth={2} />
          </g>
        )}

        {points.map((p, i) => (
          i % Math.ceil(points.length / 6) === 0 && (
            <text key={p.date} x={p.x} y={HEIGHT - 8} textAnchor="middle" className="fill-muted-foreground text-[10px]">
              {new Date(p.date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
            </text>
          )
        ))}
      </svg>

      {hovered && (
        <div
          className="pointer-events-none absolute top-2 -translate-x-1/2 rounded-md border border-border bg-popover px-2.5 py-1.5 text-xs shadow-sm"
          style={{ left: `${(hovered.x / WIDTH) * 100}%` }}
        >
          <p className="font-medium text-popover-foreground">
            {hovered.amount.toFixed(2)} {currency}
          </p>
          <p className="text-muted-foreground">
            {new Date(hovered.date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })}, {hovered.count} vente{hovered.count > 1 ? 's' : ''}
          </p>
        </div>
      )}

      <p className="mt-1 text-right text-xs text-muted-foreground">Pic : {maxAmount.toFixed(2)} {currency}</p>
    </div>
  )
}
