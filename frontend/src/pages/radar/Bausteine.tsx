import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getMarketBausteine, type MarketBaustein } from '../../api/market'
import RadarShell from './RadarShell'
import { useRadarFilters } from './useRadarFilters'

/* Was sich mehrfach verkaufen lässt. Die Pipeline-Indikation ist ein Modell mit
   sichtbaren Annahmen (Referenzfirmen × Conversion × Dealgröße) — bewusst
   verstellbar, damit die Euro-Zahl nicht wie eine Prognose aussieht. */

const eur = (n: number) =>
  n >= 1e6
    ? `${(n / 1e6).toFixed(n < 1e7 ? 1 : 0).replace('.', ',')} Mio. €`
    : `${Math.round(n / 1000).toLocaleString('de-DE')} Tsd. €`

export default function RadarBausteine() {
  const { query, patch } = useRadarFilters()
  const [rows, setRows] = useState<MarketBaustein[]>([])
  const [loading, setLoading] = useState(true)
  const [deal, setDeal] = useState(25000)
  const [conv, setConv] = useState(3)

  const key = JSON.stringify(query)
  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await getMarketBausteine(query))
    } catch {
      toast.error('Bausteine konnten nicht geladen werden.')
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])

  if (loading && !rows.length) {
    return <RadarShell><LoadingIndicator /></RadarShell>
  }

  return (
    <RadarShell>
      <div className="card p-4 mb-4 flex flex-wrap gap-6 items-center">
        <label className="text-xs text-text-muted min-w-[190px]">
          Ø Dealgröße <strong className="text-text tabular-nums">{eur(deal)}</strong>
          <input
            type="range" min={5000} max={120000} step={5000} value={deal}
            onChange={(e) => setDeal(Number(e.target.value))}
            className="w-full mt-1 accent-[color:var(--md-primary)]"
          />
        </label>
        <label className="text-xs text-text-muted min-w-[190px]">
          Conversion auf Referenzfirmen <strong className="text-text tabular-nums">{conv} %</strong>
          <input
            type="range" min={1} max={15} step={1} value={conv}
            onChange={(e) => setConv(Number(e.target.value))}
            className="w-full mt-1 accent-[color:var(--md-primary)]"
          />
        </label>
        <p className="text-xs text-text-muted flex-1 min-w-[220px]">
          Die Pipeline-Indikation ist ein Modell, keine Prognose: Referenzfirmen × Conversion × Dealgröße.
          Beide Annahmen sind hier veränderbar.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 xl:grid-cols-3 gap-3">
        {rows.map((b) => (
          <div key={b.nr} className="card p-4 flex flex-col gap-3">
            <div className="flex items-start gap-3">
              <span className="text-[11px] text-text-muted border border-outline-variant rounded-sm px-1.5 py-0.5 shrink-0">
                Baustein {b.nr}
              </span>
              <div>
                <h3 className="text-sm font-medium text-text">{b.titel}</h3>
                {b.was && <p className="text-xs text-text-muted mt-1">{b.was}</p>}
              </div>
            </div>

            <div className="text-2xl font-semibold text-text tracking-tight">
              {b.treffer}{' '}
              <span className="text-sm font-normal text-text-muted">
                Produkte im aktuellen Filter verkaufbar
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {[
                [b.reach.toLocaleString('de-DE'), 'erreichbare Referenzfirmen'],
                [eur(b.reach * (conv / 100) * deal), 'Pipeline-Indikation'],
                [b.avg_score || '–', 'Ø Opportunity Score'],
                [b.kategorien, 'Kategorien'],
              ].map(([v, l]) => (
                <div key={String(l)} className="rounded-sm bg-surface-low px-2.5 py-2">
                  <div className="text-sm font-semibold text-text tabular-nums">{v}</div>
                  <div className="text-[10px] text-text-muted">{l}</div>
                </div>
              ))}
            </div>

            {b.warum && (
              <p className="text-xs text-text-muted border-l-2 border-outline-variant pl-3">{b.warum}</p>
            )}
            {b.vorsicht && (
              <p className="text-xs text-text-muted border-l-2 border-warning pl-3">
                <strong className="text-warning">Vorsicht:</strong> {b.vorsicht}
              </p>
            )}

            <button
              type="button"
              className="btn-secondary text-xs self-start mt-auto"
              disabled={!b.treffer}
              onClick={() => patch({ baustein: String(b.nr) })}
            >
              Produkte dieses Bausteins filtern
            </button>
          </div>
        ))}
      </div>
    </RadarShell>
  )
}
