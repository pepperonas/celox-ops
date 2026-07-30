// Referenzkunden: die Firmen, die die Software der Katalog-Hersteller EINSETZEN.
//
// Das ist der eigentliche Lead-Weg des Marktradars — nicht dem Hersteller eine
// Partnerschaft verkaufen, sondern dem Anwender eine Aufsatzlösung: „Sie arbeiten mit
// [Software], ich baue [Baustein] darauf." Das Muster von bcsbook.
//
// Bewusst eine schlichte Arbeitsliste, keine Kacheln: Der Ablauf ist sichten,
// ankreuzen, übernehmen — bei tausenden Zeilen zählt Dichte, nicht Gestaltung.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import Icon from '../../components/Icon'
import Select from '../../components/Select'
import {
  getMarketReferenceCompanies,
  getMarketReferenceStats,
  referencesToPipeline,
  updateMarketReference,
  type MarketReferenceGroup,
  type MarketReferenceStats,
} from '../../api/market'
import RadarShell from './RadarShell'

const PAGE_SIZE = 50

/** Was der Score bedeutet — im Kopf der Liste erklärt, nicht versteckt. */
const TEIL_LABEL: Record<string, string> = {
  mehrfachnutzung: 'nutzt mehrere Systeme',
  baustein: 'Baustein passt',
  umfeld: 'Umfeld (Produkt-Score)',
  ansprechbar: 'Website bekannt',
}

const ORG_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlich',
  konzern: 'Konzern',
  mittelstand: 'Mittelstand',
  unbekannt: 'Typ offen',
}

const ORG_KLASSE: Record<string, string> = {
  oeffentlich: 'bg-accent/10 text-accent',
  konzern: 'bg-purple/10 text-purple',
  mittelstand: 'bg-surface-container text-text-muted',
  unbekannt: 'bg-surface-container text-text-muted',
}

export default function References() {
  const [items, setItems] = useState<MarketReferenceGroup[]>([])
  const [offen, setOffen] = useState<Set<string>>(new Set())
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('neu')
  const [webFilter, setWebFilter] = useState('alle')
  const [sort, setSort] = useState('score')
  const [nurMehrfach, setNurMehrfach] = useState(false)
  const [orgFilter, setOrgFilter] = useState('alle')
  const [stats, setStats] = useState<MarketReferenceStats | null>(null)
  const [gewaehlt, setGewaehlt] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [laedt, setLaedt] = useState(true)

  const laden = useCallback(async () => {
    setLaedt(true)
    try {
      const r = await getMarketReferenceCompanies({
        page,
        page_size: PAGE_SIZE,
        q: q.trim() || undefined,
        status: status === 'alle' ? undefined : status,
        mit_baustein: webFilter === 'alle' ? undefined : webFilter === 'ja',
        nur_mehrfach: nurMehrfach || undefined,
        orgtyp: orgFilter === 'alle' ? undefined : orgFilter,
        sort,
      })
      setItems(r.items)
      setTotal(r.total)
    } catch {
      toast.error('Referenzkunden konnten nicht geladen werden.')
    }
    setLaedt(false)
  }, [page, q, status, webFilter, nurMehrfach, orgFilter, sort])

  useEffect(() => { void laden() }, [laden])
  useEffect(() => { getMarketReferenceStats().then(setStats).catch(() => undefined) }, [])
  // Auswahl beim Filterwechsel leeren: Sie bezieht sich auf Zeilen, die nicht mehr
  // sichtbar sind — ein Übernehmen würde sonst Unerwartetes anlegen.
  useEffect(() => {
    setGewaehlt(new Set())
  }, [page, q, status, webFilter, nurMehrfach, orgFilter, sort])

  const alleSichtbarGewaehlt = items.length > 0
    && items.every((i) => gewaehlt.has(i.company_norm))

  const umschalten = (id: string) => {
    setGewaehlt((v) => {
      const n = new Set(v)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  const uebernehmen = async () => {
    // Pro ausgewählter FIRMA alle ihre Referenz-IDs mitgeben: Die Namens-Dedup in
    // reference_to_pipeline legt EINEN Lead an und hängt die Briefings der weiteren
    // Systeme an — genau das, was man im Gespräch braucht.
    const ids = items.filter((i) => gewaehlt.has(i.company_norm))
      .flatMap((i) => i.reference_ids)
    if (!ids.length) return
    setBusy(true)
    try {
      const r = await referencesToPipeline(ids, true)
      const teile = [`${r.created.length} neu angelegt`]
      if (r.linked.length) teile.push(`${r.linked.length} mit vorhandenen Leads verknüpft`)
      if (r.failed.length) teile.push(`${r.failed.length} fehlgeschlagen`)
      toast.success(teile.join(', '))
      setGewaehlt(new Set())
      await laden()
    } catch {
      toast.error('Übernahme fehlgeschlagen.')
    }
    setBusy(false)
  }

  const verwerfen = async (g: MarketReferenceGroup) => {
    // Optimistisch: Die Zeile verschwindet sofort aus der „offen"-Ansicht. Verworfen
    // wird die ganze Firma, also alle ihre Referenz-Zeilen.
    setItems((v) => v.filter((x) => x.company_norm !== g.company_norm))
    try {
      await Promise.all(g.reference_ids.map(
        (id) => updateMarketReference(id, { status: 'verworfen' })))
    } catch {
      toast.error('Konnte nicht verworfen werden.')
      await laden()
    }
  }

  const seiten = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const kopf = useMemo(
    () => `${total.toLocaleString('de-DE')} Firmen` + (status === 'neu' ? ' offen' : ''),
    [total, status],
  )

  return (
    <RadarShell>
      <div className="mb-4">
        <p className="text-sm text-text-muted">
          Eine Zeile je Firma, sortiert nach dem, was die Daten hergeben. Firmen mit
          mehreren Systemen stehen oben — mehr Systeme heißt mehr Integrationsschmerz
          und zwei Gesprächseinstiege. Der Score ist keine Umsatzprognose: Zusammensetzung
          per Maus über der Zahl. Nach der Übernahme steht der Verkaufswinkel in den
          Lead-Notizen (Software, Baustein, Beleg).
        </p>
      </div>

      {/* Kennzahlen der Kundensicht. Die Mehrfachnutzer stehen bewusst vorn und sind
          anklickbar: Es ist das einzige echte Pro-Kunde-Signal im Datensatz. */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
          <div className="border border-border rounded-card p-3">
            {/* Die distinkten FIRMEN, nicht die Zeilen: Diese Seite zeigt eine Zeile je
                Firma, und 3.712 wären die Nennungen (Firma × Hersteller). Die falsche
                Zahl oben hätte der Liste darunter widersprochen. */}
            <p className="md-title-emph text-text">
              {stats.firmen_distinkt.toLocaleString('de-DE')}
            </p>
            <p className="text-[11px] text-text-muted">Firmen</p>
            <p className="text-[10px] text-text-muted">
              {stats.firmen.toLocaleString('de-DE')} Nennungen · {stats.verzeichnisse} Verzeichnisse
            </p>
          </div>
          <button
            type="button"
            onClick={() => { setNurMehrfach((v) => !v); setPage(1) }}
            className={`border rounded-card p-3 text-left md-state ${
              nurMehrfach ? 'border-accent bg-accent/5' : 'border-border'
            }`}
          >
            <p className="md-title-emph text-accent">{stats.mehrfachnutzer}</p>
            <p className="text-[11px] text-text-muted">nutzen mehrere Systeme</p>
            <p className="text-[10px] text-text-muted">
              {nurMehrfach ? 'Filter aktiv — klicken zum Lösen' : 'stärkstes Signal · filtern'}
            </p>
          </button>
          <div className="border border-border rounded-card p-3">
            <p className="md-title-emph text-text">
              {stats.mit_baustein.toLocaleString('de-DE')}
            </p>
            <p className="text-[11px] text-text-muted">Nennungen mit Baustein</p>
            <p className="text-[10px] text-text-muted">Aufsatzlösung liegt bereit</p>
          </div>
          <div className="border border-border rounded-card p-3">
            <p className="md-title-emph text-text">{stats.in_pipeline}</p>
            <p className="text-[11px] text-text-muted">Nennungen als Lead übernommen</p>
            <p className="text-[10px] text-text-muted">
              {stats.mit_website} mit bekannter Website
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 mb-3">
        <div className="min-w-[200px] flex-1">
          <label htmlFor="ref-suche" className="block text-[11px] text-text-muted mb-1">
            Firma suchen
          </label>
          <input
            id="ref-suche"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1) }}
            placeholder="z. B. Stadtwerke"
            className="w-full"
          />
        </div>
        <div className="w-40">
          <label htmlFor="ref-status" className="block text-[11px] text-text-muted mb-1">
            Stand
          </label>
          <Select
            id="ref-status"
            name="status"
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            options={[
              { value: 'neu', label: 'offen' },
              { value: 'in_pipeline', label: 'in der Pipeline' },
              { value: 'verworfen', label: 'verworfen' },
              { value: 'alle', label: 'alle' },
            ]}
          />
        </div>
        <div className="w-44">
          <label htmlFor="ref-web" className="block text-[11px] text-text-muted mb-1">
            Aufsatzlösung
          </label>
          <Select
            id="ref-web"
            name="mit_baustein"
            value={webFilter}
            onChange={(e) => { setWebFilter(e.target.value); setPage(1) }}
            options={[
              { value: 'alle', label: 'egal' },
              { value: 'ja', label: 'Baustein passt' },
              { value: 'nein', label: 'kein Baustein' },
            ]}
          />
        </div>
        <div className="w-44">
          <label htmlFor="ref-sort" className="block text-[11px] text-text-muted mb-1">
            Reihenfolge
          </label>
          <Select
            id="ref-sort"
            name="sort"
            value={sort}
            onChange={(e) => { setSort(e.target.value); setPage(1) }}
            options={[
              { value: 'score', label: 'Score (lohnendste)' },
              { value: 'systeme', label: 'Anzahl Systeme' },
              { value: 'company', label: 'Name' },
            ]}
          />
        </div>
        <div className="w-40">
          <label htmlFor="ref-org" className="block text-[11px] text-text-muted mb-1">
            Typ
          </label>
          <Select
            id="ref-org"
            name="orgtyp"
            value={orgFilter}
            onChange={(e) => { setOrgFilter(e.target.value); setPage(1) }}
            options={[
              { value: 'alle', label: 'alle' },
              { value: 'oeffentlich', label: 'öffentlich' },
              { value: 'konzern', label: 'Konzern' },
              { value: 'mittelstand', label: 'Mittelstand' },
              { value: 'unbekannt', label: 'Typ offen' },
            ]}
          />
        </div>
        <button
          type="button"
          className="btn-primary text-sm"
          disabled={busy || gewaehlt.size === 0}
          onClick={uebernehmen}
        >
          {busy ? 'Übernehme…' : `${gewaehlt.size || ''} in die Pipeline`}
        </button>
      </div>

      <p className="text-xs text-text-muted mb-2">{kopf}</p>

      <div className="overflow-x-auto border border-border rounded-card">
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] uppercase tracking-wide text-text-muted">
            <tr className="border-b border-border">
              <th className="p-2 w-8">
                <input
                  type="checkbox"
                  aria-label="Alle sichtbaren auswählen"
                  checked={alleSichtbarGewaehlt}
                  onChange={() => setGewaehlt(
                    alleSichtbarGewaehlt ? new Set() : new Set(items.map((i) => i.company_norm)),
                  )}
                  className="w-4 h-4"
                />
              </th>
              <th className="p-2 w-16" title="Aus Mehrfachnutzung, passendem Baustein, Umfeld und Ansprechbarkeit — Zusammensetzung je Zeile im Tooltip">
                Score
              </th>
              <th className="p-2">Firma</th>
              <th className="p-2">nutzt</th>
              <th className="p-2 w-24">Stand</th>
              <th className="p-2 w-20" />
            </tr>
          </thead>
          <tbody>
            {laedt && (
              <tr><td colSpan={6} className="p-6 text-center text-text-muted">lädt…</td></tr>
            )}
            {!laedt && items.length === 0 && (
              <tr><td colSpan={6} className="p-6 text-center text-text-muted">
                Keine Firmen für diesen Filter.
              </td></tr>
            )}
            {!laedt && items.map((r) => (
              <tr key={r.company_norm} className="border-b border-border/50 last:border-0">
                <td className="p-2">
                  <input
                    type="checkbox"
                    aria-label={`${r.company} auswählen`}
                    checked={gewaehlt.has(r.company_norm)}
                    onChange={() => umschalten(r.company_norm)}
                    className="w-4 h-4"
                  />
                </td>
                <td className="p-2">
                  {/* Der Score mit seiner Zerlegung im Titel: Wer die Reihenfolge
                      anzweifelt, muss sehen können, woraus sie entsteht. */}
                  <span
                    className="inline-flex items-center gap-1.5"
                    title={Object.entries(r.score_teile)
                      .filter(([, v]) => v > 0)
                      .map(([k, v]) => `${TEIL_LABEL[k] ?? k}: +${v}`)
                      .join('\n') || 'keine Signale'}
                  >
                    <span className="text-text font-semibold tabular-nums">{r.score}</span>
                    <span className="w-8 h-1.5 rounded-full bg-surface-container overflow-hidden">
                      <span className="block h-full bg-accent" style={{ width: `${r.score}%` }} />
                    </span>
                  </span>
                </td>
                <td className="p-2">
                  <Link to={`/radar/kunden/${encodeURIComponent(r.company_norm)}`}
                        className="text-text hover:text-accent">
                    {r.company}
                  </Link>
                  {r.systeme > 1 && (
                    <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-medium"
                          title="Diese Firma steht im Referenzverzeichnis mehrerer Hersteller">
                      {r.systeme} Systeme
                    </span>
                  )}
                  <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${
                    ORG_KLASSE[r.orgtyp] ?? ORG_KLASSE.unbekannt
                  }`}>
                    {ORG_LABEL[r.orgtyp] ?? r.orgtyp}
                  </span>
                  {/* Kennzeichen, was schon angereichert ist — ohne die Detailseite
                      zu öffnen. Reihenfolge = Nützlichkeit im Gespräch. */}
                  {(r.decision_maker || r.phone || r.email || r.website) && (
                    <span className="ml-2 inline-flex items-center gap-1 align-middle"
                          title={[r.decision_maker && `Geschäftsführung: ${r.decision_maker}`,
                                  r.phone && `Telefon: ${r.phone}`,
                                  r.email && `E-Mail: ${r.email}`,
                                  r.website].filter(Boolean).join('\n')}>
                      {r.decision_maker && <Icon name="user" size={12} className="text-success" />}
                      {r.phone && <Icon name="phone" size={12} className="text-success" />}
                      {r.email && <Icon name="mail" size={12} className="text-success" />}
                      {r.website && !r.email && !r.phone && (
                        <Icon name="globe" size={12} className="text-text-muted" />
                      )}
                    </span>
                  )}
                </td>
                <td className="p-2 text-text-muted align-top">
                  {/* Alle Systeme der Firma. Mehr als eines wird eingeklappt: Bei
                      50 Zeilen zählt Dichte, und das erste System reicht meist zum
                      Erkennen. */}
                  {(offen.has(r.company_norm) ? r.produkte : r.produkte.slice(0, 1))
                    .map((sys) => (
                      <div key={sys.reference_id} className="mb-0.5 last:mb-0">
                        <a href={sys.source_url} target="_blank" rel="noopener noreferrer"
                           title="Beleg: Referenzverzeichnis des Herstellers"
                           className="text-text-muted hover:text-text">
                          {sys.produkt}
                        </a>
                        {sys.baustein_titel && (
                          <span className="block text-[11px] text-accent/90"
                                title="Aufsatzlösung, die auf diese Software passt">
                            → Baustein {sys.baustein_nr}: {sys.baustein_titel}
                          </span>
                        )}
                      </div>
                    ))}
                  {r.produkte.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setOffen((v) => {
                        const n = new Set(v)
                        if (n.has(r.company_norm)) n.delete(r.company_norm)
                        else n.add(r.company_norm)
                        return n
                      })}
                      className="text-[11px] text-accent"
                    >
                      {offen.has(r.company_norm)
                        ? 'weniger'
                        : r.produkte.length === 2
                          ? '+ 1 weiteres System'
                          : `+ ${r.produkte.length - 1} weitere Systeme`}
                    </button>
                  )}
                </td>
                <td className="p-2">
                  {r.status === 'in_pipeline' ? (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-success/10 text-success">
                      Lead
                    </span>
                  ) : r.status === 'verworfen' ? (
                    <span className="text-[11px] text-text-muted">verworfen</span>
                  ) : (
                    <span className="text-[11px] text-text-muted">offen</span>
                  )}
                </td>
                <td className="p-2 text-right align-top">
                  {r.status === 'neu' && (
                    <button
                      type="button"
                      onClick={() => verwerfen(r)}
                      title="Verwerfen"
                      aria-label={`${r.company} verwerfen`}
                      className="md-state w-8 h-8 grid place-items-center rounded-lg text-text-muted"
                    >
                      <Icon name="close" size={15} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {seiten > 1 && (
        <div className="flex items-center justify-between mt-3 text-sm">
          <button
            type="button"
            className="btn-secondary text-sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            zurück
          </button>
          <span className="text-text-muted">Seite {page} von {seiten}</span>
          <button
            type="button"
            className="btn-secondary text-sm"
            disabled={page >= seiten}
            onClick={() => setPage((p) => p + 1)}
          >
            weiter
          </button>
        </div>
      )}
    </RadarShell>
  )
}
