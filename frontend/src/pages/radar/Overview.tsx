import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import {
  getMarketProducts,
  getMarketStats,
  type MarketProduct,
  type MarketStats,
} from '../../api/market'
import ProductCard from './ProductCard'
import ProductDialog from './ProductDialog'
import RadarShell from './RadarShell'
import { Hist, OpportunityMap, RankBar } from './RadarCharts'
import { useRadarFilters } from './useRadarFilters'

function Kpi({ value, label, hint, wide }: { value: string | number; label: string; hint?: string; wide?: boolean }) {
  return (
    <div className={`card p-4 ${wide ? 'sm:col-span-2' : ''}`}>
      <div className={`font-semibold text-text tracking-tight ${wide ? 'text-3xl' : 'text-2xl'}`}>{value}</div>
      <div className="text-xs text-text-muted mt-0.5">{label}</div>
      {hint && <div className="text-[11px] text-text-muted/80 mt-1.5">{hint}</div>}
    </div>
  )
}

function Panel({ title, sub, children, wide }: { title: string; sub?: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={`card p-4 ${wide ? 'lg:col-span-2' : ''}`}>
      <div className="flex items-baseline gap-2 mb-3">
        <h3 className="text-sm font-medium text-text">{title}</h3>
        {sub && <span className="text-xs text-text-muted">{sub}</span>}
      </div>
      {children}
    </div>
  )
}

export default function RadarOverview() {
  const { query, patch } = useRadarFilters()
  const [stats, setStats] = useState<MarketStats | null>(null)
  const [products, setProducts] = useState<MarketProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState<MarketProduct | null>(null)

  const key = JSON.stringify(query)
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, p] = await Promise.all([getMarketStats(query), getMarketProducts(query)])
      setStats(s)
      setProducts(p)
    } catch {
      toast.error('Marktradar konnte nicht geladen werden.')
    }
    setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])

  const onChanged = (next: MarketProduct) =>
    setProducts((prev) => prev.map((x) => (x.id === next.id ? next : x)))

  return (
    <RadarShell>
      {loading && !stats ? (
        <LoadingIndicator />
      ) : !stats || stats.produkte === 0 ? (
        <div className="card p-8 text-center text-text-muted text-sm">
          Keine Treffer. Filter zurücksetzen — oder oben rechts den Katalog einspielen,
          falls der Marktradar noch leer ist.
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Kpi wide value={stats.referenzen.toLocaleString('de-DE')} label="erreichbare Referenzfirmen"
                 hint={`über ${stats.produkte} Produkte · ${stats.verzeichnisse} mit öffentlichem Verzeichnis`} />
            <Kpi value={stats.prio_a} label="Priorität A" hint={`${Math.round((stats.prio_a / stats.produkte) * 100)} % der Treffer`} />
            <Kpi value={stats.hersteller} label="Hersteller" />
            <Kpi value={stats.marketplace} label="mit Marktplatz" hint="skaliert ohne Direktvertrieb" />
            <Kpi value={stats.regulatorik} label="mit Regulatorik" hint="terminierter Anlass" />
            <Kpi value={stats.avg_lead} label="Ø Lead-Score" />
            <Kpi value={stats.avg_business} label="Ø Business-Score" />
            <Kpi value={stats.in_pipeline} label="in der Pipeline" hint={`${stats.offen} noch offen`} />
            <Kpi value={stats.integration_leicht} label="Integration leicht" hint="schneller erster Proof" />
          </div>

          <div>
            <div className="flex items-baseline gap-3 mb-3">
              <h3 className="text-sm font-medium text-text">Zuerst ansehen</h3>
              <span className="text-xs text-text-muted">höchster Opportunity Score im aktuellen Filter</span>
            </div>
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
              {products.slice(0, 3).map((p, i) => (
                <ProductCard key={p.id} p={p} rank={i + 1} onOpen={setOpen} />
              ))}
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-3">
            <Panel wide title="Chancen-Landkarte" sub="Klick öffnet das Dossier">
              <OpportunityMap products={products} onPick={setOpen} />
            </Panel>
            <Panel title="Top-Branchen" sub="größte Skalierung über Kunden hinweg">
              <RankBar rows={stats.branchen} onPick={(b) => patch({ branche: b })} />
            </Panel>
            <Panel title="Top-Kategorien">
              <RankBar rows={stats.kategorien_top} onPick={(k) => patch({ kategorie: k })} />
            </Panel>
            <Panel title="Regulatorischer Verkaufsdruck" sub="Anlässe mit Frist">
              <RankBar rows={stats.reg_top} onPick={(r) => patch({ regulatorik: r })} />
            </Panel>
            <Panel title="Opportunity Score" sub="Verteilung der Treffer">
              <Hist rows={stats.score_bins} />
            </Panel>
            <Panel title="Lead-Score" sub="Zugang zu den Firmen">
              <Hist rows={stats.lead_hist} />
            </Panel>
            <Panel title="Business-Score" sub="Hebel beim Kunden">
              <Hist rows={stats.business_hist} />
            </Panel>
            <Panel title="Prioritäten">
              <Hist rows={stats.prio_bins} height={130} />
            </Panel>
            <Panel title="Integrationsaufwand">
              <Hist rows={stats.int_bins} height={130} />
            </Panel>
          </div>
        </div>
      )}

      {open && <ProductDialog product={open} onClose={() => setOpen(null)} onChanged={onChanged} />}
    </RadarShell>
  )
}
