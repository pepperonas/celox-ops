// Referenzkunden: die Firmen, die die Software der Katalog-Hersteller EINSETZEN.
//
// Das ist der eigentliche Lead-Weg des Marktradars — nicht dem Hersteller eine
// Partnerschaft verkaufen, sondern dem Anwender eine Aufsatzlösung: „Sie arbeiten mit
// [Software], ich baue [Baustein] darauf." Das Muster von bcsbook.
//
// Bewusst eine schlichte Arbeitsliste, keine Kacheln: Der Ablauf ist sichten,
// ankreuzen, übernehmen — bei tausenden Zeilen zählt Dichte, nicht Gestaltung.
import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import Icon from '../../components/Icon'
import Select from '../../components/Select'
import {
  getMarketReferences,
  referencesToPipeline,
  updateMarketReference,
  type MarketReference,
} from '../../api/market'
import RadarShell from './RadarShell'

const PAGE_SIZE = 100

export default function References() {
  const [items, setItems] = useState<MarketReference[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('neu')
  const [webFilter, setWebFilter] = useState('alle')
  const [gewaehlt, setGewaehlt] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [laedt, setLaedt] = useState(true)

  const laden = useCallback(async () => {
    setLaedt(true)
    try {
      const r = await getMarketReferences({
        page,
        page_size: PAGE_SIZE,
        q: q.trim() || undefined,
        status: status === 'alle' ? undefined : status,
        mit_website: webFilter === 'alle' ? undefined : webFilter === 'ja',
      })
      setItems(r.items)
      setTotal(r.total)
    } catch {
      toast.error('Referenzkunden konnten nicht geladen werden.')
    }
    setLaedt(false)
  }, [page, q, status, webFilter])

  useEffect(() => { void laden() }, [laden])
  // Auswahl beim Filterwechsel leeren: Sie bezieht sich auf Zeilen, die nicht mehr
  // sichtbar sind — ein Übernehmen würde sonst Unerwartetes anlegen.
  useEffect(() => { setGewaehlt(new Set()) }, [page, q, status, webFilter])

  const alleSichtbarGewaehlt = items.length > 0 && items.every((i) => gewaehlt.has(i.id))

  const umschalten = (id: string) => {
    setGewaehlt((v) => {
      const n = new Set(v)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  const uebernehmen = async () => {
    const ids = [...gewaehlt]
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

  const verwerfen = async (r: MarketReference) => {
    // Optimistisch: Die Zeile verschwindet sofort aus der „neu"-Ansicht.
    setItems((v) => v.filter((x) => x.id !== r.id))
    try {
      await updateMarketReference(r.id, { status: 'verworfen' })
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
          Firmen, die die Software eines Katalog-Herstellers nachweislich einsetzen —
          laut seinem eigenen Referenzverzeichnis. Der Verkaufswinkel steht nach der
          Übernahme in den Lead-Notizen: welche Software, welcher Baustein, welcher Beleg.
        </p>
      </div>

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
        <div className="w-40">
          <label htmlFor="ref-web" className="block text-[11px] text-text-muted mb-1">
            Website
          </label>
          <Select
            id="ref-web"
            name="mit_website"
            value={webFilter}
            onChange={(e) => { setWebFilter(e.target.value); setPage(1) }}
            options={[
              { value: 'alle', label: 'egal' },
              { value: 'ja', label: 'vorhanden' },
              { value: 'nein', label: 'fehlt' },
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
                    alleSichtbarGewaehlt ? new Set() : new Set(items.map((i) => i.id)),
                  )}
                  className="w-4 h-4"
                />
              </th>
              <th className="p-2">Firma</th>
              <th className="p-2">nutzt</th>
              <th className="p-2 w-24">Stand</th>
              <th className="p-2 w-20" />
            </tr>
          </thead>
          <tbody>
            {laedt && (
              <tr><td colSpan={5} className="p-6 text-center text-text-muted">lädt…</td></tr>
            )}
            {!laedt && items.length === 0 && (
              <tr><td colSpan={5} className="p-6 text-center text-text-muted">
                Keine Firmen für diesen Filter.
              </td></tr>
            )}
            {!laedt && items.map((r) => (
              <tr key={r.id} className="border-b border-border/50 last:border-0">
                <td className="p-2">
                  <input
                    type="checkbox"
                    aria-label={`${r.company} auswählen`}
                    checked={gewaehlt.has(r.id)}
                    onChange={() => umschalten(r.id)}
                    className="w-4 h-4"
                  />
                </td>
                <td className="p-2">
                  <span className="text-text">{r.company}</span>
                  {r.website && (
                    <a
                      href={r.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent ml-2 text-xs"
                    >
                      {r.website.replace(/^https?:\/\//, '')}
                    </a>
                  )}
                </td>
                <td className="p-2 text-text-muted">
                  {r.produkt}
                  {r.hersteller && <span className="text-[11px]"> · {r.hersteller}</span>}
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
                <td className="p-2 text-right">
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Beleg: Referenzverzeichnis des Herstellers"
                    className="md-state inline-grid place-items-center w-8 h-8 rounded-lg text-text-muted"
                  >
                    <Icon name="globe" size={15} />
                  </a>
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
