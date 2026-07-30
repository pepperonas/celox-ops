import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getMarketProducts, type MarketProduct } from '../../api/market'
import ProductCard from './ProductCard'
import ProductDialog from './ProductDialog'
import RadarShell from './RadarShell'
import { useRadarFilters } from './useRadarFilters'

const SORTS: { key: string; label: string }[] = [
  { key: 'score', label: 'Opportunity Score' },
  { key: 'refs', label: 'Referenzen' },
  { key: 'lead', label: 'Lead-Score' },
  { key: 'business', label: 'Business-Score' },
  { key: 'produkt', label: 'Produkt A–Z' },
]

export default function RadarOpportunities() {
  const { query } = useRadarFilters()
  const [rows, setRows] = useState<MarketProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [sort, setSort] = useState('score')
  const [alle, setAlle] = useState(false)
  const [open, setOpen] = useState<MarketProduct | null>(null)

  const key = JSON.stringify(query)
  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await getMarketProducts(query, sort, sort === 'produkt' ? 'asc' : 'desc'))
    } catch {
      toast.error('Chancen konnten nicht geladen werden.')
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, sort])

  useEffect(() => { load() }, [load])

  const onChanged = (next: MarketProduct) =>
    setRows((prev) => prev.map((x) => (x.id === next.id ? next : x)))

  const sichtbar = alle ? rows : rows.slice(0, 24)

  return (
    <RadarShell>
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <span className="text-sm text-text-muted">
          <strong className="text-text tabular-nums">{rows.length}</strong> Treffer
        </span>
        <label className="text-xs text-text-muted flex items-center gap-2 ml-auto">
          sortiert nach
          <select value={sort} onChange={(e) => setSort(e.target.value)} className="input-field text-sm">
            {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </label>
      </div>

      {loading && !rows.length ? (
        <LoadingIndicator />
      ) : rows.length === 0 ? (
        <div className="card p-8 text-center text-text-muted text-sm">Keine Treffer für diesen Filter.</div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {sichtbar.map((p, i) => (
              <ProductCard key={p.id} p={p} rank={sort === 'score' ? i + 1 : undefined} onOpen={setOpen} />
            ))}
          </div>
          {rows.length > 24 && (
            <div className="text-center mt-4">
              <button type="button" className="btn-secondary text-sm" onClick={() => setAlle((v) => !v)}>
                {alle ? 'nur die besten 24' : `alle ${rows.length} anzeigen`}
              </button>
            </div>
          )}
        </>
      )}

      {open && <ProductDialog product={open} onClose={() => setOpen(null)} onChanged={onChanged} />}
    </RadarShell>
  )
}
