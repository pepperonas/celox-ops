import { useEffect, useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import {
  getMarketFacets,
  type MarketFacets,
} from '../../api/market'
import { INT_ALL, PRIO_ALL, REF_ALL, useRadarFilters } from './useRadarFilters'

/* Gemeinsame Hülle aller Radar-Seiten: Kopf, Unternavigation und die EINE
   Filterleiste. Bewusst eine Leiste über allem, was sie beeinflusst — Filter je
   Diagramm würden Trefferliste und Grafik auseinanderlaufen lassen. */

const TABS = [
  { to: '/radar', end: true, label: 'Übersicht' },
  { to: '/radar/chancen', label: 'Top-Chancen' },
  // Die Kunden der Hersteller — der eigentliche Lead-Weg, deshalb weit vorn.
  { to: '/radar/kunden', label: 'Referenzkunden' },
  { to: '/radar/bausteine', label: 'Bausteine' },
  { to: '/radar/hersteller', label: 'Hersteller' },
  { to: '/radar/kategorien', label: 'Kategorien' },
]

const REF_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlich',
  teilweise: 'teilweise',
  auf_anfrage: 'auf Anfrage',
  unklar: 'unklar',
}

const STATUS_LABEL: Record<string, string> = {
  neu: 'neu',
  gesichtet: 'gesichtet',
  vorgemerkt: 'vorgemerkt',
  in_pipeline: 'in Pipeline',
  verworfen: 'verworfen',
}

function Seg({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2.5 py-1 rounded-sm text-xs border transition-colors ${
        on
          ? 'bg-surface-high border-outline-variant text-text'
          : 'bg-surface-low border-transparent text-text-muted hover:text-text'
      }`}
    >
      {children}
    </button>
  )
}

export default function RadarShell({ children }: { children: ReactNode }) {
  const { filters, patch, toggle, reset, active } = useRadarFilters()
  const [facets, setFacets] = useState<MarketFacets | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    getMarketFacets().then(setFacets).catch(() => undefined)
  }, [])

  return (
    <div className="max-w-content">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
        <div>
          <h2 className="text-2xl font-semibold text-text tracking-tight">Marktradar</h2>
          <p className="text-text-muted text-sm mt-1">
            Softwareprodukte mit öffentlichem Referenzverzeichnis als Lead-Quelle
            {facets?.stand && ` · Katalogstand ${facets.stand}`}
            {facets ? ` · ${facets.gesamt} Einträge` : ''}
          </p>
        </div>
      </div>

      <nav className="flex gap-1 mb-4 border-b border-outline-variant overflow-x-auto">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={{ pathname: t.to, search: window.location.search }}
            end={t.end}
            className={({ isActive }) =>
              `px-3 py-2 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors ${
                isActive
                  ? 'border-md-primary text-text font-medium'
                  : 'border-transparent text-text-muted hover:text-text'
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>

      {/* Filterleiste */}
      <div className="card p-3 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="search"
            value={filters.q}
            onChange={(e) => patch({ q: e.target.value })}
            placeholder="Produkt, Prozess, KI-Idee, Hersteller …"
            className="input-field text-sm flex-1 min-w-[220px]"
          />
          <select
            value={filters.kategorie}
            onChange={(e) => patch({ kategorie: e.target.value })}
            className="input-field text-sm"
          >
            <option value="">alle Kategorien</option>
            {facets?.kategorien.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
          <select
            value={filters.branche}
            onChange={(e) => patch({ branche: e.target.value })}
            className="input-field text-sm"
          >
            <option value="">alle Branchen</option>
            {facets?.branchen.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
          <button type="button" className="btn-secondary text-sm" onClick={() => setOpen((v) => !v)}>
            {open ? 'weniger' : 'mehr Filter'}
          </button>
          {active && (
            <button type="button" className="text-xs text-text-muted hover:text-text" onClick={reset}>
              zurücksetzen
            </button>
          )}
        </div>

        {open && (
          <div className="mt-3 pt-3 border-t border-outline-variant grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <div className="text-xs text-text-muted mb-1.5">Priorität</div>
              <div className="flex gap-1.5">
                {PRIO_ALL.map((p) => (
                  <Seg key={p} on={filters.prio.includes(p)} onClick={() => toggle('prio', p, PRIO_ALL)}>
                    {p}
                  </Seg>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">Integrationsaufwand</div>
              <div className="flex gap-1.5">
                {INT_ALL.map((i) => (
                  <Seg key={i} on={filters.integration.includes(i)} onClick={() => toggle('integration', i, INT_ALL)}>
                    {i}
                  </Seg>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">Referenzverzeichnis</div>
              <div className="flex gap-1.5 flex-wrap">
                {REF_ALL.map((r) => (
                  <Seg key={r} on={filters.ref_status.includes(r)} onClick={() => toggle('ref_status', r, REF_ALL)}>
                    {REF_LABEL[r]}
                  </Seg>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">Bearbeitungsstand</div>
              <select
                value={filters.bearbeitung[0] ?? ''}
                onChange={(e) => patch({ bearbeitung: e.target.value || null })}
                className="input-field text-sm w-full"
              >
                <option value="">alle</option>
                {(facets?.bearbeitung ?? []).map((s) => (
                  <option key={s} value={s}>{STATUS_LABEL[s] ?? s}</option>
                ))}
              </select>
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">Regulatorik</div>
              <select
                value={filters.regulatorik}
                onChange={(e) => patch({ regulatorik: e.target.value })}
                className="input-field text-sm w-full"
              >
                <option value="">alle</option>
                {facets?.regulatorik.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2 justify-end">
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <input
                  type="checkbox"
                  checked={filters.marketplace}
                  onChange={(e) => patch({ marketplace: e.target.checked ? '1' : null })}
                />
                nur mit Marktplatz
              </label>
              <label className="flex items-center gap-2 text-sm text-text-muted">
                <input
                  type="checkbox"
                  checked={filters.hat_regulatorik}
                  onChange={(e) => patch({ reg: e.target.checked ? '1' : null })}
                />
                nur mit Regulatorik-Anlass
              </label>
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">
                Lead-Score ≥ <span className="text-text tabular-nums">{filters.min_lead}</span>
              </div>
              <input
                type="range" min={1} max={10} value={filters.min_lead}
                onChange={(e) => patch({ min_lead: e.target.value === '1' ? null : e.target.value })}
                className="w-full accent-[color:var(--md-primary)]"
              />
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">
                Business-Score ≥ <span className="text-text tabular-nums">{filters.min_business}</span>
              </div>
              <input
                type="range" min={1} max={10} value={filters.min_business}
                onChange={(e) => patch({ min_business: e.target.value === '1' ? null : e.target.value })}
                className="w-full accent-[color:var(--md-primary)]"
              />
            </div>
            <div>
              <div className="text-xs text-text-muted mb-1.5">
                Referenzen ≥ <span className="text-text tabular-nums">{filters.min_refs}</span>
              </div>
              <input
                type="range" min={0} max={260} step={10} value={filters.min_refs}
                onChange={(e) => patch({ min_refs: e.target.value === '0' ? null : e.target.value })}
                className="w-full accent-[color:var(--md-primary)]"
              />
            </div>
          </div>
        )}

        {filters.baustein !== null && (
          <div className="mt-3 text-xs text-text-muted flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-surface-high border border-outline-variant">
              nur Produkte aus Baustein {filters.baustein}
            </span>
            <button type="button" className="hover:text-text" onClick={() => patch({ baustein: null })}>
              entfernen
            </button>
          </div>
        )}
      </div>

      {children}
    </div>
  )
}
