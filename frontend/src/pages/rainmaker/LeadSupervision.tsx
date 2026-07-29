// Aufsicht über die Lead-Arbeit: Papierkorb + Änderungsprotokoll.
//
// Beides auf einer Seite, weil es dieselbe Frage beantwortet: Was ist mit meinen
// Leads passiert und wie nehme ich es zurück? Nur für den Bereichs-Inhaber — die
// Aufsicht über die Arbeit eines Verkäufers darf nicht bei ihm selbst liegen.
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import PageHeader from '../../components/PageHeader'
import LoadingIndicator from '../../components/LoadingIndicator'
import Icon from '../../components/Icon'
import PipelineNav from './PipelineNav'
import {
  getLeadChanges, getLeadTrash, purgeLead, restoreLead, revertLeadChange,
  type LeadChange, type TrashItem,
} from '../../api/leadSupervision'
import { FIELD_LABELS, changeSummary, actionLabel } from '../../utils/leadChanges'

export default function LeadSupervision() {
  const [trash, setTrash] = useState<TrashItem[]>([])
  const [retention, setRetention] = useState(30)
  const [changes, setChanges] = useState<LeadChange[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [confirmPurge, setConfirmPurge] = useState<TrashItem | null>(null)

  const load = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([getLeadTrash(), getLeadChanges()])
      setTrash(t.items)
      setRetention(t.retention_days)
      setChanges(c)
    } catch {
      toast.error('Papierkorb konnte nicht geladen werden.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { void load() }, [load])

  const doRestore = async (item: TrashItem) => {
    setBusy(item.id)
    try {
      await restoreLead(item.id)
      toast.success(`„${item.company}" ist zurück in der Pipeline.`)
      await load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Wiederherstellen fehlgeschlagen.')
    }
    setBusy(null)
  }

  const doPurge = async (item: TrashItem) => {
    setConfirmPurge(null)
    setBusy(item.id)
    try {
      await purgeLead(item.id)
      toast.success('Endgültig entfernt.')
      await load()
    } catch {
      toast.error('Entfernen fehlgeschlagen.')
    }
    setBusy(null)
  }

  const doRevert = async (entry: LeadChange) => {
    setBusy(entry.id)
    try {
      const res = await revertLeadChange(entry.id)
      if (res.reverted_fields.length === 0) {
        toast(
          'Nichts zurückgenommen — alle Felder wurden seither erneut geändert.',
          { icon: <Icon name="warning" size={18} /> },
        )
      } else if (res.skipped_fields.length > 0) {
        toast.success(
          `${res.reverted_fields.length} Feld(er) zurückgesetzt. `
          + `Übersprungen (seither geändert): ${res.skipped_fields
            .map((f) => FIELD_LABELS[f] || f).join(', ')}`,
        )
      } else {
        toast.success('Änderung zurückgenommen.')
      }
      await load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Rücknahme fehlgeschlagen.')
    }
    setBusy(null)
  }

  if (loading) return <div className="pb-24"><PipelineNav /><LoadingIndicator /></div>

  return (
    <div className="pb-24">
      <PipelineNav />
      <PageHeader
        title="Papierkorb & Änderungen"
        subtitle={`Gelöschte Leads bleiben ${retention} Tage wiederherstellbar`}
      />

      {/* ---- Papierkorb ---- */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-text mb-2">
          <Icon name="trash" size={15} className="mr-1.5 -mt-0.5" />
          Papierkorb ({trash.length})
        </h2>
        {trash.length === 0 ? (
          <p className="text-sm text-text-muted py-4">
            Der Papierkorb ist leer.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-muted border-b border-border">
                  <th className="py-2 pr-3 font-medium">Firma</th>
                  <th className="py-2 pr-3 font-medium">Gelöscht von</th>
                  <th className="py-2 pr-3 font-medium">Wann</th>
                  <th className="py-2 pr-3 font-medium">Frist</th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {trash.map((t) => (
                  <tr key={t.id} className="border-b border-border/50">
                    <td className="py-2 pr-3">
                      <span className="text-text break-words">{t.company}</span>
                      {t.contact_name && (
                        <span className="text-text-muted"> · {t.contact_name}</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-text-muted">{t.deleted_by || '—'}</td>
                    <td className="py-2 pr-3 text-text-muted">
                      {t.deleted_at ? new Date(t.deleted_at).toLocaleString('de-DE') : '—'}
                    </td>
                    <td className="py-2 pr-3">
                      <span className={t.days_left <= 3 ? 'text-warning' : 'text-text-muted'}>
                        {t.days_left} Tage
                      </span>
                    </td>
                    <td className="py-2 whitespace-nowrap">
                      <button
                        onClick={() => doRestore(t)}
                        disabled={busy === t.id}
                        className="btn-secondary !py-1.5 !px-3 !text-xs mr-2"
                      >
                        Zurückholen
                      </button>
                      <button
                        onClick={() => setConfirmPurge(t)}
                        disabled={busy === t.id}
                        className="btn-secondary !py-1.5 !px-3 !text-xs !text-danger"
                      >
                        Endgültig
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ---- Änderungsprotokoll ---- */}
      <section>
        <h2 className="text-sm font-semibold text-text mb-1">
          <Icon name="clock" size={15} className="mr-1.5 -mt-0.5" />
          Letzte Änderungen ({changes.length})
        </h2>
        <p className="text-xs text-text-muted mb-3">
          Protokolliert werden Änderungen zugeschnittener Rollen (Verkäufer).
          Eine Rücknahme setzt nur Felder zurück, die seither niemand angefasst hat.
        </p>
        {changes.length === 0 ? (
          <p className="text-sm text-text-muted py-4">Noch keine Änderungen protokolliert.</p>
        ) : (
          <ul className="space-y-2">
            {changes.map((c) => (
              <li key={c.id}
                  className={`border rounded-card p-3 ${c.reverted_at
                    ? 'border-border bg-surface/40' : 'border-border bg-surface-high'}`}>
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-1">
                  <span className="text-sm font-medium text-text break-words">
                    {c.lead_id ? (
                      <Link to={`/pipeline/leads/${c.lead_id}`} className="hover:underline">
                        {c.lead_company}
                      </Link>
                    ) : c.lead_company}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-text-muted">
                    {actionLabel(c.action)}
                  </span>
                  <span className="text-xs text-text-muted">
                    {c.actor} · {c.created_at ? new Date(c.created_at).toLocaleString('de-DE') : ''}
                  </span>
                  {c.reverted_at && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-accent">
                      zurückgenommen
                    </span>
                  )}
                </div>
                {changeSummary(c.changes).map((line) => (
                  <p key={line.field} className="text-xs text-text-muted break-words">
                    <span className="text-text">{line.label}:</span> {line.from} → {line.to}
                  </p>
                ))}
                {c.action === 'update' && !c.reverted_at && (
                  <button
                    onClick={() => doRevert(c)}
                    disabled={busy === c.id}
                    className="btn-secondary !py-1.5 !px-3 !text-xs mt-2"
                  >
                    Zurücknehmen
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {confirmPurge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
          <div className="fixed inset-0" onClick={() => setConfirmPurge(null)} />
          <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-6 max-w-md w-full mx-4
                          animate-modal-in">
            <h3 className="text-lg font-semibold text-text mb-2">Endgültig entfernen?</h3>
            <p className="text-sm text-text-muted mb-5">
              „{confirmPurge.company}" wird unwiderruflich gelöscht — samt Aktivitäten
              und Website-Befunden. Es gibt danach kein Zurückholen.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmPurge(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button onClick={() => doPurge(confirmPurge)} className="btn-primary !bg-danger">
                Endgültig löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
