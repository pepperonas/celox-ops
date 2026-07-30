import { Bar } from 'react-chartjs-2'
import '../../utils/charts'
import type { MarketBucket, MarketProduct } from '../../api/market'

/* Diagramme des Marktradars.
   Rangbalken und Histogramme laufen über Chart.js (Hausstandard, siehe Analytics).
   Die Chancen-Landkarte ist bewusst handgezeichnetes SVG: für ein Blasendiagramm
   müsste `BubbleController` global registriert werden — ein Eingriff in eine von
   allen Seiten geteilte Datei für genau eine Grafik. */

const ACCENT = '#7cb0ff'
const MUTED = '#9aa6b5'
const GRID = '#2c333d'
const SURFACE = '#0e1318'

/** Prioritätsstufen als Ordinal-Rampe EINER Farbe (hell = dringlichste Stufe).
 *  Drei kategoriale Farben wären für eine geordnete Größe die falsche Kodierung. */
export const PRIO_COLOR: Record<string, string> = { A: '#a9c9ff', B: '#7cb0ff', C: '#3f6fa8' }

const baseOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
} as const

export function RankBar({ rows, onPick }: { rows: MarketBucket[]; onPick?: (key: string) => void }) {
  if (!rows.length) return <div className="text-text-muted text-sm">keine Daten</div>
  return (
    <div style={{ height: Math.max(120, rows.length * 26 + 20) }}>
      <Bar
        data={{
          labels: rows.map((r) => r.label),
          datasets: [{ data: rows.map((r) => r.value), backgroundColor: ACCENT, borderRadius: 4, barThickness: 12 }],
        }}
        options={{
          ...baseOpts,
          indexAxis: 'y' as const,
          onClick: onPick
            ? (_e, els) => { const i = els[0]?.index; if (i != null) onPick(rows[i].key ?? rows[i].label) }
            : undefined,
          scales: {
            x: { grid: { color: GRID }, ticks: { color: MUTED, precision: 0 }, border: { display: false } },
            y: { grid: { display: false }, ticks: { color: MUTED }, border: { display: false } },
          },
        }}
      />
    </div>
  )
}

export function Hist({ rows, height = 150 }: { rows: MarketBucket[]; height?: number }) {
  if (!rows.length) return <div className="text-text-muted text-sm">keine Daten</div>
  return (
    <div style={{ height }}>
      <Bar
        data={{
          labels: rows.map((r) => r.label),
          datasets: [{ data: rows.map((r) => r.value), backgroundColor: ACCENT, borderRadius: 4 }],
        }}
        options={{
          ...baseOpts,
          scales: {
            x: { grid: { display: false }, ticks: { color: MUTED }, border: { display: false } },
            y: { grid: { color: GRID }, ticks: { color: MUTED, precision: 0 }, border: { display: false } },
          },
        }}
      />
    </div>
  )
}

/** Lead × Business, Fläche = Referenzen, Farbe = Prioritätsstufe. */
export function OpportunityMap({
  products,
  onPick,
}: {
  products: MarketProduct[]
  onPick: (p: MarketProduct) => void
}) {
  const W = 720
  const H = 340
  const m = { t: 12, r: 14, b: 34, l: 38 }
  const pw = W - m.l - m.r
  const ph = H - m.t - m.b
  const X = (v: number) => m.l + ((v - 0.5) / 10) * pw
  const Y = (v: number) => m.t + ph - ((v - 0.5) / 10) * ph
  const maxRefs = Math.max(1, ...products.map((p) => p.refs))
  const R = (v: number) => 4 + Math.sqrt(v / maxRefs) * 12
  // Deterministischer Versatz: identische Score-Paare lägen sonst exakt übereinander.
  const jit = (s: string) => {
    let x = 0
    for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) % 1000
    return (x / 1000 - 0.5) * 0.5
  }

  if (!products.length) return <div className="text-text-muted text-sm">keine Treffer</div>

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Chancen-Landkarte: Lead-Score gegen Business-Score">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((v) => (
          <g key={v}>
            <line x1={X(v)} y1={m.t} x2={X(v)} y2={m.t + ph} stroke={GRID} strokeWidth={1} />
            <line x1={m.l} y1={Y(v)} x2={m.l + pw} y2={Y(v)} stroke={GRID} strokeWidth={1} />
          </g>
        ))}
        {[2, 4, 6, 8, 10].map((v) => (
          <g key={`t${v}`}>
            <text x={X(v)} y={H - 16} textAnchor="middle" fill={MUTED} fontSize={11}>{v}</text>
            <text x={m.l - 8} y={Y(v) + 4} textAnchor="end" fill={MUTED} fontSize={11}>{v}</text>
          </g>
        ))}
        <text x={m.l + pw / 2} y={H - 2} textAnchor="middle" fill={MUTED} fontSize={11}>
          Lead-Score → besserer Zugang zu den Firmen
        </text>
        {[...products]
          .sort((a, b) => b.refs - a.refs)
          .map((p) => (
            <circle
              key={p.id}
              cx={X(p.lead + jit(p.id))}
              cy={Y(p.business + jit(p.id + 'y'))}
              r={R(p.refs)}
              fill={PRIO_COLOR[p.prio]}
              fillOpacity={0.72}
              stroke={SURFACE}
              strokeWidth={2}
              className="cursor-pointer"
              onClick={() => onPick(p)}
            >
              <title>{`${p.produkt} — ${p.vendor}\nScore ${p.score} · Lead ${p.lead} · Business ${p.business} · ${p.refs} Referenzen`}</title>
            </circle>
          ))}
      </svg>
      <div className="flex gap-4 mt-2 text-xs text-text-muted">
        {(['A', 'B', 'C'] as const).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <i className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: PRIO_COLOR[k] }} />
            Priorität {k}
          </span>
        ))}
        <span className="ml-auto">Fläche = Referenzen · rechts oben = beste Kombination</span>
      </div>
    </div>
  )
}
