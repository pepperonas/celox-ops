import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import Icon from '../../components/Icon'
import {
  marketToPipeline,
  updateMarketProduct,
  type MarketProduct,
  type MarketStatus,
} from '../../api/market'

/* Dossier eines Katalogeintrags — und der eine Knopf, um den Hersteller als Lead
   in die Pipeline zu übernehmen. createPortal, weil `.page-enter` den Vorfahren
   transformiert (Repo-Regel). */

const STATUS: { value: MarketStatus; label: string }[] = [
  { value: 'neu', label: 'neu' },
  { value: 'gesichtet', label: 'gesichtet' },
  { value: 'vorgemerkt', label: 'vorgemerkt' },
  { value: 'in_pipeline', label: 'in Pipeline' },
  { value: 'verworfen', label: 'verworfen' },
]

const BD_LABEL: Record<string, string> = {
  business: 'Business-Hebel',
  lead: 'Zugang zu Firmen',
  reach: 'Reichweite',
  prio: 'Priorität',
  integration: 'Integration',
  marketplace: 'Marktplatz',
  regulatorik: 'Regulatorik',
}

const REF_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlich',
  teilweise: 'teilweise',
  auf_anfrage: 'auf Anfrage',
  unklar: 'unklar',
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null
  return (
    <div>
      <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1.5">{title}</h4>
      <ul className="list-disc pl-5 space-y-1 text-sm text-text-muted">
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </div>
  )
}

export default function ProductDialog({
  product,
  onClose,
  onChanged,
}: {
  product: MarketProduct
  onClose: () => void
  onChanged: (p: MarketProduct) => void
}) {
  const nav = useNavigate()
  const [p, setP] = useState(product)
  const [note, setNote] = useState(product.ops_note ?? '')
  const [busy, setBusy] = useState(false)

  const maxPoints = Math.max(1, ...p.breakdown.map((b) => b.points))

  const save = async (data: { status?: MarketStatus; ops_note?: string | null }) => {
    setBusy(true)
    try {
      const next = await updateMarketProduct(p.id, data)
      setP(next)
      onChanged(next)
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setBusy(false)
  }

  const push = async (force = false) => {
    setBusy(true)
    try {
      const r = await marketToPipeline(p.id, { force })
      toast.success(
        r.created
          ? `„${r.company}" als Lead angelegt.`
          : `Mit bestehendem Lead „${r.company}" verknüpft.`,
      )
      const next = { ...p, status: 'in_pipeline' as MarketStatus, rainmaker_lead_id: r.lead_id }
      setP(next)
      onChanged(next)
      nav(`/pipeline/leads/${r.lead_id}`)
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: { message?: string } } } }
      if (err.response?.status === 409) {
        const msg = err.response.data?.detail?.message ?? 'Lead existiert bereits. Trotzdem verknüpfen?'
        if (window.confirm(msg)) {
          setBusy(false)
          return push(true)
        }
      } else {
        toast.error('Übernahme fehlgeschlagen.')
      }
    }
    setBusy(false)
  }

  return createPortal(
    <div className="fixed inset-0 bg-black/85 flex items-start justify-center z-50 p-4 overflow-y-auto" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-surface border border-border rounded-dialog w-full max-w-3xl my-8 animate-modal-in"
      >
        <header className="flex items-start gap-4 p-5 border-b border-outline-variant sticky top-0 bg-surface rounded-t-dialog z-10">
          <div>
            <h3 className="text-lg font-semibold text-text">{p.produkt}</h3>
            <p className="text-sm text-text-muted mt-0.5">{p.hersteller} · {p.kategorie}</p>
          </div>
          <button type="button" onClick={onClose} className="ml-auto btn-secondary text-sm" aria-label="Schließen">✕</button>
        </header>

        <div className="p-5 space-y-5">
          <div className="flex items-center gap-3">
            <span className="text-3xl font-semibold text-text tracking-tight">{p.score}</span>
            <div className="flex-1 h-1.5 rounded-full bg-surface-high overflow-hidden">
              <div className="h-full bg-md-primary rounded-full" style={{ width: `${p.score}%` }} />
            </div>
            <span className="text-xs uppercase tracking-wide text-text-muted">Opportunity Score</span>
          </div>

          <div className="flex flex-wrap gap-1.5 text-xs">
            <span className="px-2 py-0.5 rounded-full bg-md-primary-container text-on-primary-container">Priorität {p.prio}</span>
            <span className="px-2 py-0.5 rounded-full border border-outline-variant text-text-muted">Integration {p.int_level}</span>
            {p.marketplace && (
              <span className="px-2 py-0.5 rounded-full border border-success/40 text-success">
                ⬡ {p.mp_evidence.join(' · ')}
              </span>
            )}
            {p.reg.map((r) => (
              <span key={r} className="px-2 py-0.5 rounded-full border border-warning/40 text-warning">§ {r}</span>
            ))}
            {p.self_compete && (
              <span className="px-2 py-0.5 rounded-full border border-danger/50 text-danger inline-flex items-center gap-1">
                <Icon name="warning" size={12} /> Hersteller besetzt den Use Case selbst
              </span>
            )}
            <span className="px-2 py-0.5 rounded-full border border-outline-variant text-text-muted">
              Verzeichnis {REF_LABEL[p.ref_status]}
            </span>
          </div>

          {/* Arbeitsstand + Übernahme */}
          <div className="rounded-card border border-outline-variant p-4 space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-text-muted">Bearbeitungsstand</span>
              {STATUS.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  disabled={busy}
                  onClick={() => save({ status: s.value })}
                  className={`px-2.5 py-1 rounded-sm text-xs border transition-colors ${
                    p.status === s.value
                      ? 'bg-surface-high border-outline-variant text-text'
                      : 'bg-surface-low border-transparent text-text-muted hover:text-text'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>

            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onBlur={() => note !== (p.ops_note ?? '') && save({ ops_note: note || null })}
              rows={2}
              placeholder="Eigene Notiz zu diesem Eintrag …"
              className="input-field text-sm w-full"
            />

            <div className="flex items-center gap-3 flex-wrap">
              {p.rainmaker_lead_id ? (
                <>
                  <span className="text-sm text-success">In der Pipeline.</span>
                  <button
                    type="button"
                    className="btn-secondary text-sm"
                    onClick={() => nav(`/pipeline/leads/${p.rainmaker_lead_id}`)}
                  >
                    Lead öffnen
                  </button>
                </>
              ) : (
                <button type="button" className="btn-primary text-sm" disabled={busy} onClick={() => push()}>
                  {busy ? 'Übernehme…' : `„${p.vendor}" in die Pipeline übernehmen`}
                </button>
              )}
              <span className="text-xs text-text-muted">
                Legt den <strong>Hersteller</strong> als Lead an — mit Briefing aus KI-Idee, Pain und Nutzen.
              </span>
            </div>
          </div>

          <div>
            <h4 className="text-xs uppercase tracking-wide text-text-muted mb-2">Score-Aufschlüsselung</h4>
            <div className="space-y-1">
              {p.breakdown.map((b) => (
                <div key={b.key} className="grid grid-cols-[130px_1fr_52px] gap-3 items-center text-xs">
                  <span className="text-text-muted">{BD_LABEL[b.key] ?? b.key}</span>
                  <span className="h-1.5 rounded-full bg-surface-high overflow-hidden block">
                    <span className="block h-full bg-md-primary" style={{ width: `${(b.points / maxPoints) * 100}%` }} />
                  </span>
                  <span className="text-right tabular-nums text-text-muted">+{b.points.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid sm:grid-cols-4 gap-2">
            {[
              [p.lead, 'Lead-Score'],
              [p.business, 'Business-Score'],
              [p.refs, 'Referenzen'],
              [p.prio, 'Priorität'],
            ].map(([v, l]) => (
              <div key={String(l)} className="rounded-sm bg-surface-low p-2.5">
                <div className="text-lg font-semibold text-text tabular-nums">{v}</div>
                <div className="text-[11px] text-text-muted">{l}</div>
              </div>
            ))}
          </div>

          <div className="grid sm:grid-cols-2 gap-5">
            <List title="Unterstützte Geschäftsprozesse" items={p.prozesse} />
            <List title="Wer arbeitet täglich damit" items={p.nutzer} />
            <List title="Manuelle Tätigkeiten — der Ansatzpunkt" items={p.pains} />
            <List title="Denkbare KI-/Automatisierungslösungen" items={p.ki} />
            <List title="Branchen" items={p.branchen} />
            <div className="space-y-3 text-sm">
              {p.nutzen && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Einsparpotenzial</h4>
                  <p className="text-text-muted">{p.nutzen}</p>
                </div>
              )}
              {p.zielgruppe && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Zielgruppe</h4>
                  <p className="text-text-muted">{p.zielgruppe}</p>
                </div>
              )}
              {p.kunden && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Kundenbasis</h4>
                  <p className="text-text-muted">{p.kunden}</p>
                </div>
              )}
            </div>
          </div>

          {p.integration && (
            <div>
              <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Integration</h4>
              <p className="text-sm text-text-muted">{p.integration}</p>
            </div>
          )}
          {p.notiz && (
            <div>
              <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Notiz aus der Recherche</h4>
              <p className="text-sm text-text-muted">{p.notiz}</p>
            </div>
          )}

          <div>
            <h4 className="text-xs uppercase tracking-wide text-text-muted mb-1">Referenzverzeichnis</h4>
            <a href={p.ref_url} target="_blank" rel="noopener noreferrer" className="text-sm text-accent break-all">
              {p.ref_url}
            </a>
            <span className="text-xs text-text-muted"> — Live-Check: {p.url_ok ? 'erreichbar' : p.url_geprueft}</span>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
