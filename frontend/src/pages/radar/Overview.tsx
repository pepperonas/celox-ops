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
import { Link } from 'react-router-dom'
import {
  getMarketReferenceCompanies,
  getMarketReferenceStats,
  referencesToPipeline,
  type MarketReferenceGroup,
  type MarketReferenceStats,
} from '../../api/market'
import CustomerSuggestion from './CustomerSuggestion'
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
  // Stabiler Schlüssel des Filters — als Abhängigkeit für das Nachladen.
  const filterKey = JSON.stringify(query)
  const [stats, setStats] = useState<MarketStats | null>(null)
  // Kundensicht: Der Marktradar bewertet jetzt die Anwender, nicht die Hersteller.
  const [kunden, setKunden] = useState<MarketReferenceStats | null>(null)
  // Die Vorschläge selbst — das, worum es im Marktradar geht.
  const [vorschlaege, setVorschlaege] = useState<MarketReferenceGroup[]>([])
  const [busy, setBusy] = useState(false)
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
  // Kundenkennzahlen einmal laden — sie hängen nicht am Katalogfilter, weil die
  // Systemzahl je Firma ein Aggregat über den GESAMTEN Bestand ist.
  useEffect(() => { getMarketReferenceStats().then(setKunden).catch(() => undefined) }, [])

  // `key` hängt am Filter: Wechselt er, laden die Vorschläge neu.
  const ladeVorschlaege = useCallback(async () => {
    try {
      // Folgt dem geteilten Filter: `getMarketReferenceCompanies` liest ihn aus der
      // URL-Query, die der Client mitsendet — „Kategorie X" zeigt hier deren Kunden.
      const r = await getMarketReferenceCompanies(
        { status: 'neu', sort: 'score', page_size: 6 }, query)
      setVorschlaege(r.items)
    } catch {
      setVorschlaege([])
    }
  }, [filterKey])   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { void ladeVorschlaege() }, [ladeVorschlaege])

  const uebernehmen = async (k: MarketReferenceGroup) => {
    setBusy(true)
    try {
      const r = await referencesToPipeline(k.reference_ids, true)
      toast.success(r.created.length ? 'Als Lead angelegt.' : 'Mit vorhandenem Lead verknüpft.')
      await Promise.all([ladeVorschlaege(), getMarketReferenceStats().then(setKunden)])
    } catch {
      toast.error('Übernahme fehlgeschlagen.')
    }
    setBusy(false)
  }

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
          {/* KUNDENSICHT ZUERST. Ziel sind die Anwender der Software, nicht ihre
              Hersteller — der Katalog ist das Mittel. Vorher stand hier „Priorität A",
              „Ø Lead-Score" und „mit Marktplatz": Kennzahlen über das Mittel. */}
          {kunden && (
            <div>
              <div className="flex items-baseline justify-between gap-3 mb-2 flex-wrap">
                <h3 className="text-sm font-medium text-text">Kunden der Hersteller</h3>
                <Link to="/radar/kunden" className="text-xs text-accent">
                  alle {kunden.firmen.toLocaleString('de-DE')} ansehen →
                </Link>
              </div>
              {/* Sechs Spalten, weil die erste Kachel zwei belegt (`wide`): Mit fünf
                  fiel die letzte allein in eine neue Zeile und ließ eine Lücke. */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <Kpi wide value={kunden.firmen_distinkt.toLocaleString('de-DE')}
                     label="Firmen als Lead-Kandidat"
                     hint={`${kunden.firmen.toLocaleString('de-DE')} Nennungen aus ${kunden.verzeichnisse} Referenzverzeichnissen`} />
                <Kpi value={kunden.mehrfachnutzer} label="nutzen mehrere Systeme"
                     hint="stärkstes Signal — zwei Gesprächseinstiege" />
                <Kpi value={kunden.mit_baustein.toLocaleString('de-DE')} label="Nennungen mit Baustein"
                     hint="Aufsatzlösung liegt bereit" />
                <Kpi value={kunden.in_pipeline} label="Nennungen als Lead übernommen"
                     hint={`${kunden.offen.toLocaleString('de-DE')} offen`} />
                <Kpi value={kunden.mit_website} label="mit bekannter Website"
                     hint="Rest braucht Handrecherche" />
              </div>
            </div>
          )}

          {/* DER VORSCHLAG. Vorher standen hier Produktkarten — „diese Software ist
              interessant". Der Lead ist aber eine Firma: „diese nutzt X, biete ihr Y
              an." Produkte stehen jetzt weiter unten im Umfeld-Block. */}
          <div>
            <div className="flex items-baseline justify-between gap-3 mb-3 flex-wrap">
              <div className="flex items-baseline gap-3 flex-wrap">
                <h3 className="text-sm font-medium text-text">Zuerst ansprechen</h3>
                <span className="text-xs text-text-muted">
                  Firmen, die eine der Katalog-Softwares einsetzen — mit der Aufsatzlösung,
                  die darauf passt
                </span>
              </div>
              <Link to="/radar/kunden" className="text-xs text-accent">alle ansehen →</Link>
            </div>
            {vorschlaege.length === 0 ? (
              <p className="text-sm text-text-muted">
                Keine offenen Referenzkunden für diesen Filter.
              </p>
            ) : (
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                {vorschlaege.map((k, i) => (
                  <CustomerSuggestion key={k.company_norm} k={k} rang={i + 1}
                                      onPipeline={uebernehmen} busy={busy} />
                ))}
              </div>
            )}
          </div>

          {/* Herstellersicht als zweiter Block: das Umfeld, in dem verkauft wird. */}
          <div>
            <div className="flex items-baseline gap-3 mb-2">
              <h3 className="text-sm font-medium text-text">Umfeld: die Hersteller</h3>
              <span className="text-xs text-text-muted">
                Kennzahlen des Katalogs — das Mittel, nicht das Ziel
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <Kpi value={stats.produkte} label="Produkte" hint={`${stats.hersteller} Hersteller`} />
              <Kpi value={stats.referenzen.toLocaleString('de-DE')} label="Referenzen laut Katalog"
                   hint="Schätzung der Verzeichnisse" />
              <Kpi value={stats.prio_a} label="Priorität A" hint={`${Math.round((stats.prio_a / stats.produkte) * 100)} % der Treffer`} />
              <Kpi value={stats.marketplace} label="mit Marktplatz" hint="skaliert ohne Direktvertrieb" />
              <Kpi value={stats.regulatorik} label="mit Regulatorik" hint="terminierter Anlass" />
              <Kpi value={stats.integration_leicht} label="Integration leicht" hint="schneller erster Proof" />
            </div>
            {/* Die Software mit dem höchsten Opportunity Score — nützlich, um zu
                entscheiden, WESSEN Kundenliste sich lohnt. Deshalb hier im Umfeld,
                nicht als Vorschlag. */}
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
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
