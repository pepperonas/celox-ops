import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import PipelineNav from './PipelineNav'
import { getDuplicates, mergeDuplicatesBatch } from '../../api/rainmaker'
import type { DuplicateGroup, DuplicateMember } from '../../types'
import { buildBatchSummary, type BatchSummary, type GroupSel } from './batchSummary'

const REASON: Record<string, { label: string; cls: string; safe: boolean }> = {
  same_person: { label: 'Dieselbe Person', cls: 'text-danger', safe: true },
  firm: { label: 'Firma doppelt', cls: 'text-danger', safe: true },
  colleagues: { label: 'Verschiedene Ansprechpartner · evtl. Kollegen', cls: 'text-warning', safe: false },
  fuzzy: { label: 'Nur ähnlicher Name', cls: 'text-warning', safe: false },
}
const reasonInfo = (r: string) => REASON[r] ?? { label: r, cls: 'text-text-muted', safe: false }

function MemberRow({ m, isKeeper, checked, onKeeper, onToggle }: {
  m: DuplicateMember; isKeeper: boolean; checked: boolean; onKeeper: () => void; onToggle: () => void
}) {
  const parts = [m.contact_name, m.role].filter(Boolean).join(' · ')
  return (
    <div className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${isKeeper ? 'bg-success/10 border border-success/30' : 'bg-surface-high'}`}>
      <label className="flex items-center gap-1.5 cursor-pointer shrink-0" title="Als Behalten-Lead wählen">
        <input type="radio" checked={isKeeper} onChange={onKeeper} />
        <span className="text-[10px] text-text-muted">behalten</span>
      </label>
      <div className="min-w-0 flex-1">
        <div className="text-text truncate">
          <span className="font-medium">{m.company}</span>
          {parts && <span className="text-text-muted"> — {parts}</span>}
        </div>
        <div className="text-xs text-text-muted truncate">
          {[m.email, m.website?.replace(/^https?:\/\//, ''), m.phone].filter(Boolean).join(' · ') || '—'}
        </div>
      </div>
      <div className="text-xs text-text-muted text-right shrink-0">
        <div>{m.source || '—'}</div>
        <div>{m.activity_count > 0 ? `${m.activity_count} Akt.` : 'keine Akt.'}</div>
      </div>
      {!isKeeper && (
        <label className="flex items-center gap-1 cursor-pointer shrink-0 text-danger" title="Löschen/zusammenführen">
          <input type="checkbox" checked={checked} onChange={onToggle} />
        </label>
      )}
    </div>
  )
}

function GroupCard({ group, sel, onInclude, onKeeper, onToggleDup, onDismiss }: {
  group: DuplicateGroup
  sel: GroupSel
  onInclude: (v: boolean) => void
  onKeeper: (id: string) => void
  onToggleDup: (id: string) => void
  onDismiss: () => void
}) {
  const info = reasonInfo(group.reason)
  const keeper = group.members.find((m) => m.id === sel.keeperId) ?? group.members[0]
  const dupCount = sel.dupIds.filter((id) => id !== sel.keeperId).length
  return (
    <div className={`bg-surface-container border rounded-card p-4 mb-4 animate-md-enter transition-colors duration-short ${sel.included ? 'border-accent' : 'border-border'}`}>
      <div className="flex items-center justify-between mb-3 gap-2">
        <label className="flex items-center gap-2 cursor-pointer min-w-0">
          <input type="checkbox" checked={sel.included} onChange={(e) => onInclude(e.target.checked)} className="shrink-0" />
          <span className={`text-sm font-semibold ${info.cls} truncate`}>{info.label}</span>
          {!info.safe && <span className="text-[10px] text-warning shrink-0">⚠ prüfen</span>}
          <span className="text-xs text-text-muted shrink-0">· {Math.round(group.score * 100)}% · {group.members.length} Leads</span>
        </label>
        <button onClick={onDismiss} className="text-xs text-text-muted hover:text-text shrink-0">Kein Duplikat</button>
      </div>

      <div className="space-y-1.5">
        {group.members.map((m) => (
          <MemberRow key={m.id} m={m} isKeeper={m.id === sel.keeperId}
                     checked={sel.dupIds.includes(m.id)}
                     onKeeper={() => onKeeper(m.id)} onToggle={() => onToggleDup(m.id)} />
        ))}
      </div>

      <div className="text-xs text-text-muted mt-2">
        Behalten: „{keeper?.company}"{dupCount > 0 ? ` · ${dupCount} löschen` : ' · nichts gewählt'}
      </div>
    </div>
  )
}

function ConfirmDialog({ summary, onConfirm, onCancel, busy }: {
  summary: BatchSummary; onConfirm: () => void; onCancel: () => void; busy: boolean
}) {
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={() => !busy && onCancel()} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-6 max-w-md w-full mx-4 animate-modal-in">
        <h3 className="text-lg font-semibold text-text mb-3">Zusammenführen bestätigen</h3>
        <p className="text-sm text-text mb-3">
          <strong>{summary.groupCount}</strong> Gruppe{summary.groupCount === 1 ? '' : 'n'} werden zusammengeführt:
        </p>
        <ul className="text-sm text-text-muted space-y-1 mb-4">
          <li>· <strong className="text-text">{summary.deleteCount}</strong> Lead{summary.deleteCount === 1 ? '' : 's'} werden gelöscht</li>
          <li>· <strong className="text-text">{summary.activityCount}</strong> Aktivität{summary.activityCount === 1 ? '' : 'en'} werden auf den Behalten-Lead übernommen</li>
        </ul>
        {summary.colleagueCount > 0 && (
          <div className="text-xs text-warning bg-warning/10 border border-warning/30 rounded-lg px-3 py-2 mb-3">
            ⚠ {summary.colleagueCount} Gruppe{summary.colleagueCount === 1 ? '' : 'n'} mit verschiedenen Ansprechpartnern
            („Kollegen"/ähnliche Namen) sind dabei — bitte sicher sein, dass das wirklich dieselbe Firma ist.
          </div>
        )}
        {summary.overlaps && (
          <div className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-lg px-3 py-2 mb-3">
            ⚠ Ein Lead kommt in mehreren gewählten Gruppen vor — diese Gruppen werden übersprungen.
          </div>
        )}
        <p className="text-xs text-text-muted mb-4">Diese Aktion kann nicht rückgängig gemacht werden.</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} disabled={busy} className="btn-secondary">Abbrechen</button>
          <button onClick={onConfirm} disabled={busy} className="btn-danger">
            {busy ? 'Führe zusammen…' : 'Zusammenführen'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default function Duplicates() {
  const [groups, setGroups] = useState<DuplicateGroup[] | null>(null)
  const [sel, setSel] = useState<Record<number, GroupSel>>({})
  const [resolved, setResolved] = useState<Set<number>>(new Set())
  const [confirm, setConfirm] = useState<BatchSummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [checking, setChecking] = useState(false)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const load = async (manual = false) => {
    setChecking(true)
    setResolved(new Set()); setConfirm(null)
    try {
      const gs = await getDuplicates()
      const init: Record<number, GroupSel> = {}
      gs.forEach((g, i) => {
        init[i] = {
          included: reasonInfo(g.reason).safe,      // nur sichere Typen vorwählen
          keeperId: g.suggested_keeper_id,
          dupIds: g.members.filter((m) => m.id !== g.suggested_keeper_id).map((m) => m.id),
        }
      })
      setGroups(gs); setSel(init)
      setLastChecked(new Date())
      // Ohne Toast wirkt ein manuelles „Erneut prüfen" mit leerem Ergebnis
      // wirkungslos (die Ansicht ändert sich nicht).
      if (manual) {
        toast.success(
          gs.length === 0
            ? 'Keine Duplikate gefunden.'
            : `${gs.length} Verdachtsgruppe${gs.length === 1 ? '' : 'n'} gefunden.`,
        )
      }
    } catch {
      toast.error('Duplikate konnten nicht geladen werden.'); setGroups([])
    }
    setChecking(false)
  }
  useEffect(() => { load() }, [])

  const patch = (i: number, p: Partial<GroupSel>) =>
    setSel((prev) => ({ ...prev, [i]: { ...prev[i], ...p } }))

  const setKeeper = (i: number, id: string) =>
    setSel((prev) => ({ ...prev, [i]: { ...prev[i], keeperId: id, dupIds: prev[i].dupIds.filter((d) => d !== id) } }))

  const toggleDup = (i: number, id: string) =>
    setSel((prev) => {
      const cur = prev[i]
      const has = cur.dupIds.includes(id)
      return { ...prev, [i]: { ...cur, dupIds: has ? cur.dupIds.filter((d) => d !== id) : [...cur.dupIds, id] } }
    })

  const dismiss = (i: number) => {
    setResolved((prev) => new Set(prev).add(i))
    patch(i, { included: false })
  }

  const visible = useMemo(
    () => (groups ?? []).map((g, i) => ({ g, i })).filter(({ i }) => !resolved.has(i)),
    [groups, resolved],
  )

  const summary = useMemo(() => buildBatchSummary(groups ?? [], sel), [groups, sel])

  const selectAllSafe = () =>
    setSel((prev) => {
      const next = { ...prev }
      visible.forEach(({ g, i }) => { if (reasonInfo(g.reason).safe) next[i] = { ...next[i], included: true } })
      return next
    })
  const deselectAll = () =>
    setSel((prev) => {
      const next = { ...prev }
      Object.keys(next).forEach((k) => { next[+k] = { ...next[+k], included: false } })
      return next
    })

  const runBatch = async () => {
    if (!confirm) return
    setBusy(true)
    try {
      const r = await mergeDuplicatesBatch(confirm.merges)
      toast.success(
        `${r.merged_groups} Gruppe${r.merged_groups === 1 ? '' : 'n'} zusammengeführt · ${r.deleted_leads} gelöscht`
        + (r.moved_activities > 0 ? ` · ${r.moved_activities} Aktivitäten übernommen` : '')
        + (r.failed.length > 0 ? ` · ${r.failed.length} übersprungen` : '') + '.')
      if (r.failed.length > 0) {
        toast(r.failed.map((f) => `„${f.company}": ${f.reason}`).join('\n'), { icon: '⚠', duration: 6000 })
      }
      await load()
    } catch {
      toast.error('Batch-Zusammenführung fehlgeschlagen.')
    }
    setBusy(false); setConfirm(null)
  }

  return (
    <div className="max-w-3xl">
      <PageHeader title="Duplikate" subtitle="Ähnliche Leads prüfen und zusammenführen" />
      <PipelineNav />

      {/* Prüf-Status — gibt „Erneut prüfen" sichtbares Feedback, auch wenn sich
          das Ergebnis (weiterhin keine Duplikate) nicht ändert. */}
      {(checking || lastChecked) && (
        <div className="flex items-center gap-2 text-xs text-text-muted mb-3">
          {checking ? (
            <>
              <span className="md-spinner !w-3.5 !h-3.5 !border-2" />
              <span>Prüfe auf Duplikate…</span>
            </>
          ) : (
            <span>
              Zuletzt geprüft:{' '}
              {lastChecked!.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
        </div>
      )}

      {groups === null && !checking && <p className="text-text-muted text-sm py-8 text-center">Lade…</p>}
      {groups !== null && visible.length === 0 && (
        <div className="text-center py-16">
          <div className="text-4xl mb-2">🎉</div>
          <p className="text-text-muted">Keine Duplikate gefunden.</p>
          <button onClick={() => load(true)} disabled={checking} className="btn-secondary text-sm mt-4 disabled:opacity-50">
            {checking ? 'Prüfe…' : 'Erneut prüfen'}
          </button>
        </div>
      )}

      {visible.length > 0 && (
        <>
          {/* Aktionsleiste */}
          <div className="sticky top-0 z-10 -mx-1 px-1 py-2 mb-3 bg-bg/80 backdrop-blur flex flex-wrap items-center gap-2">
            <button onClick={selectAllSafe} className="btn-secondary text-xs !py-1.5">✓ Alle sicheren auswählen</button>
            <button onClick={deselectAll} className="text-xs text-text-muted hover:text-text px-2">Abwählen</button>
            <span className="text-xs text-text-muted ml-auto">
              {summary.groupCount} gewählt · {summary.deleteCount} löschen · {summary.activityCount} Akt.
            </span>
            <button
              onClick={() => summary.groupCount > 0 && setConfirm(summary)}
              disabled={summary.groupCount === 0}
              className="btn-danger text-sm disabled:opacity-40"
            >
              {summary.groupCount} zusammenführen
            </button>
          </div>

          <p className="text-xs text-text-muted mb-3">
            E-Mail/Website sind bereits eindeutig — dies sind Firmennamen-Treffer. „Kollegen"/ähnliche Namen
            sind bewusst nicht vorausgewählt (⚠). Beim Zusammenführen bleibt ein Lead, die anderen werden
            gelöscht, Aktivitäten wandern mit.
          </p>

          {visible.map(({ g, i }) => (
            <GroupCard
              key={i} group={g} sel={sel[i]}
              onInclude={(v) => patch(i, { included: v })}
              onKeeper={(id) => setKeeper(i, id)}
              onToggleDup={(id) => toggleDup(i, id)}
              onDismiss={() => dismiss(i)}
            />
          ))}
        </>
      )}

      {confirm && (
        <ConfirmDialog summary={confirm} busy={busy} onConfirm={runBatch} onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}
