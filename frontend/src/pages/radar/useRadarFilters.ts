import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { MarketQuery } from '../../api/market'

/* Filterzustand liegt in der URL, nicht im Komponentenstate.
   Grund: Die fünf Radar-Seiten teilen sich denselben Filter. Läge er im State
   einer Seite, wäre er beim Wechsel auf „Bausteine" weg — und genau der Wechsel
   ist der Arbeitsablauf (erst filtern, dann in anderer Sicht ansehen).
   Nebeneffekt: ein Blick lässt sich als Link ablegen. */

export const PRIO_ALL = ['A', 'B', 'C']
export const INT_ALL = ['leicht', 'mittel', 'schwer']
export const REF_ALL = ['oeffentlich', 'teilweise', 'auf_anfrage', 'unklar']

export interface RadarFilters {
  q: string
  kategorie: string
  branche: string
  regulatorik: string
  prio: string[]
  integration: string[]
  ref_status: string[]
  bearbeitung: string[]
  marketplace: boolean
  hat_regulatorik: boolean
  min_lead: number
  min_business: number
  min_refs: number
  baustein: number | null
}

const csv = (v: string | null, fallback: string[]) =>
  v === null ? fallback : v ? v.split(',').filter(Boolean) : []

export function useRadarFilters() {
  const [sp, setSp] = useSearchParams()

  const filters: RadarFilters = useMemo(
    () => ({
      q: sp.get('q') ?? '',
      kategorie: sp.get('kategorie') ?? '',
      branche: sp.get('branche') ?? '',
      regulatorik: sp.get('regulatorik') ?? '',
      prio: csv(sp.get('prio'), PRIO_ALL),
      integration: csv(sp.get('integration'), INT_ALL),
      ref_status: csv(sp.get('ref_status'), REF_ALL),
      bearbeitung: csv(sp.get('bearbeitung'), []),
      marketplace: sp.get('marketplace') === '1',
      hat_regulatorik: sp.get('reg') === '1',
      min_lead: Number(sp.get('min_lead') ?? 1),
      min_business: Number(sp.get('min_business') ?? 1),
      min_refs: Number(sp.get('min_refs') ?? 0),
      baustein: sp.get('baustein') ? Number(sp.get('baustein')) : null,
    }),
    [sp],
  )

  const patch = useCallback(
    (next: Record<string, string | null | undefined>) => {
      const p = new URLSearchParams(sp)
      for (const [k, v] of Object.entries(next)) {
        if (v === null || v === undefined || v === '') p.delete(k)
        else p.set(k, v)
      }
      setSp(p, { replace: true })
    },
    [sp, setSp],
  )

  /** Mehrfachauswahl umschalten. Leert die Auswahl nie vollständig — eine leere
   *  Menge würde alles ausblenden und sieht wie ein kaputter Filter aus. */
  const toggle = useCallback(
    (key: 'prio' | 'integration' | 'ref_status', value: string, all: string[]) => {
      const cur = filters[key]
      const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value]
      patch({ [key]: (next.length ? next : all).join(',') })
    },
    [filters, patch],
  )

  const reset = useCallback(() => setSp(new URLSearchParams(), { replace: true }), [setSp])

  const active =
    filters.q !== '' ||
    filters.kategorie !== '' ||
    filters.branche !== '' ||
    filters.regulatorik !== '' ||
    filters.marketplace ||
    filters.hat_regulatorik ||
    filters.min_lead > 1 ||
    filters.min_business > 1 ||
    filters.min_refs > 0 ||
    filters.baustein !== null ||
    filters.prio.length < 3 ||
    filters.integration.length < 3 ||
    filters.ref_status.length < 4 ||
    filters.bearbeitung.length > 0

  /** Auf die API-Form bringen: Vorgabewerte weglassen, damit die URL kurz bleibt. */
  const query: MarketQuery = useMemo(() => {
    const q: MarketQuery = {}
    if (filters.q) q.q = filters.q
    if (filters.kategorie) q.kategorie = filters.kategorie
    if (filters.branche) q.branche = filters.branche
    if (filters.regulatorik) q.regulatorik = filters.regulatorik
    if (filters.prio.length < 3) q.prio = filters.prio.join(',')
    if (filters.integration.length < 3) q.integration = filters.integration.join(',')
    if (filters.ref_status.length < 4) q.ref_status = filters.ref_status.join(',')
    if (filters.bearbeitung.length) q.bearbeitung = filters.bearbeitung.join(',')
    if (filters.marketplace) q.marketplace = true
    if (filters.hat_regulatorik) q.hat_regulatorik = true
    if (filters.min_lead > 1) q.min_lead = filters.min_lead
    if (filters.min_business > 1) q.min_business = filters.min_business
    if (filters.min_refs > 0) q.min_refs = filters.min_refs
    if (filters.baustein !== null) q.baustein = filters.baustein
    return q
  }, [filters])

  return { filters, query, patch, toggle, reset, active }
}
