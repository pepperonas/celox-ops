import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import {
  getMarketCategories,
  getMarketProducts,
  type MarketCategory,
  type MarketProduct,
} from '../../api/market'
import ProductDialog from './ProductDialog'
import RadarShell from './RadarShell'
import { useRadarFilters } from './useRadarFilters'

export default function RadarCategories() {
  const { query, patch } = useRadarFilters()
  const [rows, setRows] = useState<MarketCategory[]>([])
  const [products, setProducts] = useState<MarketProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState<MarketProduct | null>(null)

  const key = JSON.stringify(query)
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [c, p] = await Promise.all([getMarketCategories(query), getMarketProducts(query)])
      setRows(c)
      setProducts(p)
    } catch {
      toast.error('Kategorien konnten nicht geladen werden.')
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])

  const byCatalogId = new Map(products.map((p) => [p.catalog_id, p]))
  const onChanged = (next: MarketProduct) =>
    setProducts((prev) => prev.map((x) => (x.id === next.id ? next : x)))

  if (loading && !rows.length) return <RadarShell><LoadingIndicator /></RadarShell>

  return (
    <RadarShell>
      <div className="grid lg:grid-cols-2 xl:grid-cols-3 gap-3">
        {rows.map((c) => (
          <div key={c.kategorie} className="card p-4 flex flex-col gap-3">
            <div>
              <h3 className="text-sm font-medium text-text">{c.kategorie}</h3>
              <p className="text-xs text-text-muted mt-0.5">
                {c.produkte} Produkte · Ø Score {c.avg_score} · {c.refs.toLocaleString('de-DE')} Referenzfirmen
              </p>
            </div>

            <div className="grid grid-cols-4 gap-2">
              {[
                [c.prio_a, 'Priorität A'],
                [c.marketplace, 'mit Marktplatz'],
                [c.oeffentlich, 'öffentl. Verz.'],
                [c.avg_business, 'Ø Business'],
              ].map(([v, l]) => (
                <div key={String(l)} className="rounded-sm bg-surface-low px-2 py-1.5">
                  <div className="text-sm font-semibold text-text tabular-nums">{v}</div>
                  <div className="text-[10px] text-text-muted">{l}</div>
                </div>
              ))}
            </div>

            <div>
              <h4 className="text-[11px] uppercase tracking-wide text-text-muted mb-1.5">Top-Chancen</h4>
              <div className="flex flex-wrap gap-1.5">
                {c.top.map((t) => {
                  const p = byCatalogId.get(t.catalog_id)
                  return (
                    <button
                      key={t.catalog_id}
                      type="button"
                      disabled={!p}
                      onClick={() => p && setDialog(p)}
                      className="text-[11px] px-2 py-1 rounded-full bg-surface-low border border-outline-variant text-text-muted hover:text-text hover:border-outline transition-colors disabled:opacity-50"
                    >
                      {t.produkt} · {t.score}
                    </button>
                  )
                })}
              </div>
            </div>

            {c.top[0]?.ki && (
              <div>
                <h4 className="text-[11px] uppercase tracking-wide text-text-muted mb-1">Größter KI-Hebel</h4>
                <p className="text-xs text-text-muted">
                  <strong className="text-text">{c.top[0].produkt}:</strong> {c.top[0].ki}
                </p>
              </div>
            )}

            {c.prozesse.length > 0 && (
              <div>
                <h4 className="text-[11px] uppercase tracking-wide text-text-muted mb-1.5">Häufigste Prozesse</h4>
                <div className="flex flex-wrap gap-1">
                  {c.prozesse.map((pr) => (
                    <span key={pr.label} className="text-[10.5px] px-1.5 py-0.5 rounded-full bg-surface-low border border-outline-variant text-text-muted">
                      {pr.label} · {pr.value}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {c.risiken.length > 0 && (
              <div>
                <h4 className="text-[11px] uppercase tracking-wide text-text-muted mb-1.5">Größte Risiken</h4>
                <ul className="text-xs text-text-muted space-y-1">
                  {c.risiken.map((r) => (
                    <li key={r.catalog_id}>
                      <strong className="text-text">{r.produkt}:</strong> {r.grund.join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              type="button"
              className="btn-secondary text-xs self-start mt-auto"
              onClick={() => patch({ kategorie: c.kategorie })}
            >
              Auf diese Kategorie filtern
            </button>
          </div>
        ))}
      </div>

      {dialog && <ProductDialog product={dialog} onClose={() => setDialog(null)} onChanged={onChanged} />}
    </RadarShell>
  )
}
