import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import Icon from '../../components/Icon'
import LoadingIndicator from '../../components/LoadingIndicator'
import {
  getMarketKonzerne,
  getMarketProducts,
  getMarketVendors,
  type MarketKonzern,
  type MarketProduct,
  type MarketVendor,
  getMarketBausteine,
  type MarketBaustein,
} from '../../api/market'
import ProductDialog from './ProductDialog'
import SoftwareInfoDialog from './SoftwareInfoDialog'
import RadarShell from './RadarShell'
import { useRadarFilters } from './useRadarFilters'

export default function RadarVendors() {
  const { query } = useRadarFilters()
  const [vendors, setVendors] = useState<MarketVendor[]>([])
  const [konzerne, setKonzerne] = useState<MarketKonzern[]>([])
  const [products, setProducts] = useState<MarketProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [offen, setOffen] = useState<string | null>(null)
  const [dialog, setDialog] = useState<MarketProduct | null>(null)
  // Verbesserungspotenzial je Software — eigener Dialog, eigene Frage.
  const [info, setInfo] = useState<MarketProduct | null>(null)
  const [bausteine, setBausteine] = useState<MarketBaustein[]>([])

  const key = JSON.stringify(query)
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [v, k, p] = await Promise.all([
        getMarketVendors(query), getMarketKonzerne(query), getMarketProducts(query),
      ])
      setVendors(v)
      setKonzerne(k)
      setProducts(p)
    } catch {
      toast.error('Herstellerdaten konnten nicht geladen werden.')
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])
  // Bausteine einmal laden — der Info-Dialog ordnet sie selbst zu.
  useEffect(() => { getMarketBausteine().then(setBausteine).catch(() => undefined) }, [])

  const byCatalogId = new Map(products.map((p) => [p.catalog_id, p]))
  const onChanged = (next: MarketProduct) =>
    setProducts((prev) => prev.map((x) => (x.id === next.id ? next : x)))

  if (loading && !vendors.length) return <RadarShell><LoadingIndicator /></RadarShell>

  return (
    <RadarShell>
      {konzerne.length > 0 && (
        <div className="card p-4 mb-4">
          <div className="flex items-baseline gap-2 mb-3">
            <h3 className="text-sm font-medium text-text">Konzern-Ökosysteme</h3>
            <span className="text-xs text-text-muted">
              ein Eigentümer, mehrere Produkte — eine Partnerschaft erreicht alle
            </span>
          </div>
          <div className="space-y-2">
            {konzerne.map((k) => (
              <div key={k.konzern_slug} className="flex items-center gap-4 rounded-sm bg-surface-low px-3 py-2">
                <div className="min-w-0">
                  <div className="text-sm text-text">{k.konzern}</div>
                  <div className="text-xs text-text-muted truncate">{k.namen.join(' · ')}</div>
                </div>
                <div className="ml-auto flex gap-5 text-right shrink-0">
                  <div><div className="text-sm font-semibold text-text tabular-nums">{k.produkte}</div><div className="text-[10px] text-text-muted">Produkte</div></div>
                  <div><div className="text-sm font-semibold text-text tabular-nums">{k.refs.toLocaleString('de-DE')}</div><div className="text-[10px] text-text-muted">Referenzen</div></div>
                  <div><div className="text-sm font-semibold text-text">{k.marketplace ? '⬡' : '–'}</div><div className="text-[10px] text-text-muted">Marktplatz</div></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-text-muted mb-2">
        {vendors.length} Anbieter · sortiert nach Ø Opportunity Score · Klick zeigt die Produkte
      </div>

      <div className="space-y-2">
        {vendors.map((v) => {
          const open = offen === v.vendor_slug
          return (
            <div key={v.vendor_slug} className="card p-0 overflow-hidden">
              <button
                type="button"
                onClick={() => setOffen(open ? null : v.vendor_slug)}
                className="w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-surface-low transition-colors"
              >
                <div className="min-w-0">
                  <div className="text-sm text-text">{v.vendor}</div>
                  <div className="text-xs text-text-muted truncate">
                    {v.produkte} Produkt{v.produkte > 1 ? 'e' : ''} · {v.kategorien.join(' · ')}
                    {v.marketplace && <span className="text-success"> · Marktplatz</span>}
                    {v.reg.length > 0 && ` · § ${v.reg.slice(0, 3).join(', ')}`}
                  </div>
                </div>
                <div className="ml-auto flex gap-5 text-right shrink-0">
                  <div><div className="text-sm font-semibold text-text tabular-nums">{v.refs.toLocaleString('de-DE')}</div><div className="text-[10px] text-text-muted">Referenzen</div></div>
                  <div><div className="text-sm font-semibold text-text tabular-nums">{v.avg_lead}</div><div className="text-[10px] text-text-muted">Ø Lead</div></div>
                  <div><div className="text-sm font-semibold text-text tabular-nums">{v.avg_score}</div><div className="text-[10px] text-text-muted">Ø Score</div></div>
                </div>
              </button>
              {open && (
                <div className="px-4 pb-3 pt-1 border-t border-outline-variant flex flex-wrap gap-1.5">
                  {v.catalog_ids.map((cid) => {
                    const p = byCatalogId.get(cid)
                    if (!p) return null
                    return (
                      // Zwei Ziele je Produkt: die Pille öffnet das Dossier, das
                      // Info-Icon das Verbesserungspotenzial. Deshalb ein Paar statt
                      // eines Knopfes mit zwei Bedeutungen.
                      <span key={cid} className="inline-flex items-center gap-0.5 rounded-full
                                                 bg-surface-low border border-outline-variant
                                                 pr-0.5 hover:border-outline transition-colors">
                        <button
                          type="button"
                          onClick={() => setDialog(p)}
                          className="text-[11px] px-2 py-1 text-text-muted hover:text-text"
                        >
                          {p.produkt} · Score {p.score} · {p.refs} Ref.
                        </button>
                        <button
                          type="button"
                          onClick={() => setInfo(p)}
                          title="Was lässt sich an dieser Software verbessern?"
                          aria-label={`Verbesserungspotenzial von ${p.produkt} ansehen`}
                          className="md-state w-6 h-6 grid place-items-center rounded-full
                                     text-text-muted hover:text-accent"
                        >
                          <Icon name="info" size={13} />
                        </button>
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {dialog && <ProductDialog product={dialog} onClose={() => setDialog(null)} onChanged={onChanged} />}
      {info && (
        <SoftwareInfoDialog info={info} bausteine={bausteine} onClose={() => setInfo(null)} />
      )}
    </RadarShell>
  )
}
