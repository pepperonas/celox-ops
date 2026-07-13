import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import RainmakerNav from './RainmakerNav'
import { getDuplicates, mergeDuplicates } from '../../api/rainmaker'
import type { DuplicateGroup, DuplicateMember } from '../../types'

// Grund → Label + Farbe + ob die Duplikate vorausgewählt werden (Kollegen NICHT).
const REASON: Record<string, { label: string; cls: string; preselect: boolean }> = {
  same_person: { label: 'Dieselbe Person', cls: 'text-danger', preselect: true },
  firm: { label: 'Firma doppelt', cls: 'text-danger', preselect: true },
  colleagues: { label: 'Verschiedene Ansprechpartner · evtl. Kollegen', cls: 'text-warning', preselect: false },
  fuzzy: { label: 'Nur ähnlicher Name', cls: 'text-warning', preselect: false },
}

function reasonInfo(r: string) {
  return REASON[r] ?? { label: r, cls: 'text-text-muted', preselect: false }
}

function GroupCard({ group, onResolved }: { group: DuplicateGroup; onResolved: () => void }) {
  const info = reasonInfo(group.reason)
  const [keeperId, setKeeperId] = useState(group.suggested_keeper_id)
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(info.preselect ? group.members.filter((m) => m.id !== group.suggested_keeper_id).map((m) => m.id) : []),
  )
  const [busy, setBusy] = useState(false)

  // Keeper wechselt → aus der Auswahl nehmen
  const chooseKeeper = (id: string) => {
    setKeeperId(id)
    setSelected((prev) => { const n = new Set(prev); n.delete(id); return n })
  }
  const toggle = (id: string) => setSelected((prev) => {
    const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n
  })

  const keeper = group.members.find((m) => m.id === keeperId)!
  const dupIds = [...selected].filter((id) => id !== keeperId)
  const movedActs = group.members.filter((m) => dupIds.includes(m.id)).reduce((s, m) => s + m.activity_count, 0)

  const doMerge = async () => {
    if (dupIds.length === 0) return
    const names = group.members.filter((m) => dupIds.includes(m.id)).map((m) => `„${m.company}"`).join(', ')
    const msg = `${names} → in „${keeper.company}" zusammenführen`
      + (movedActs > 0 ? ` (${movedActs} Aktivität${movedActs === 1 ? '' : 'en'} übernehmen)` : '')
      + `. ${dupIds.length} Lead${dupIds.length === 1 ? '' : 's'} werden gelöscht. Fortfahren?`
    if (!window.confirm(msg)) return
    setBusy(true)
    try {
      const r = await mergeDuplicates(keeperId, dupIds)
      toast.success(`Zusammengeführt: ${r.merged_leads} gelöscht`
        + (r.moved_activities > 0 ? `, ${r.moved_activities} Aktivitäten übernommen` : '') + '.')
      onResolved()
    } catch {
      toast.error('Zusammenführen fehlgeschlagen.')
      setBusy(false)
    }
  }

  return (
    <div className="bg-surface-container border border-border rounded-card p-4 mb-4 animate-md-enter">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${info.cls}`}>{info.label}</span>
          <span className="text-xs text-text-muted">· {Math.round(group.score * 100)}% Konfidenz · {group.members.length} Leads</span>
        </div>
        <button onClick={onResolved} className="text-xs text-text-muted hover:text-text">Kein Duplikat</button>
      </div>

      <div className="space-y-1.5">
        {group.members.map((m) => (
          <MemberRow key={m.id} m={m} isKeeper={m.id === keeperId}
                     checked={selected.has(m.id)} onKeeper={() => chooseKeeper(m.id)} onToggle={() => toggle(m.id)} />
        ))}
      </div>

      <div className="flex items-center justify-end gap-3 mt-3">
        <span className="text-xs text-text-muted mr-auto">
          Behalten: „{keeper.company}"{dupIds.length > 0 ? ` · ${dupIds.length} löschen` : ''}
        </span>
        <button onClick={doMerge} disabled={busy || dupIds.length === 0}
                className="btn-danger text-sm disabled:opacity-40">
          {busy ? 'Führe zusammen…' : 'Zusammenführen'}
        </button>
      </div>
    </div>
  )
}

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

export default function Duplicates() {
  const [groups, setGroups] = useState<DuplicateGroup[] | null>(null)
  const [resolved, setResolved] = useState<Set<number>>(new Set())

  const load = async () => {
    setResolved(new Set())
    try {
      setGroups(await getDuplicates())
    } catch {
      toast.error('Duplikate konnten nicht geladen werden.')
      setGroups([])
    }
  }
  useEffect(() => { load() }, [])

  const visible = useMemo(
    () => (groups ?? []).map((g, i) => ({ g, i })).filter(({ i }) => !resolved.has(i)),
    [groups, resolved],
  )

  return (
    <div className="max-w-3xl">
      <PageHeader title="Duplikate" subtitle="Ähnliche Leads prüfen und zusammenführen" />
      <RainmakerNav />

      {groups === null && <p className="text-text-muted text-sm py-8 text-center">Lade…</p>}
      {groups !== null && visible.length === 0 && (
        <div className="text-center py-16">
          <div className="text-4xl mb-2">🎉</div>
          <p className="text-text-muted">Keine Duplikate gefunden.</p>
          <button onClick={load} className="btn-secondary text-sm mt-4">Erneut prüfen</button>
        </div>
      )}
      {visible.length > 0 && (
        <>
          <p className="text-xs text-text-muted mb-3">
            {visible.length} Verdachtsgruppe{visible.length === 1 ? '' : 'n'}. E-Mail/Website sind bereits eindeutig —
            dies sind Firmennamen-Treffer. „Kollegen"-Gruppen sind bewusst nicht vorausgewählt.
          </p>
          {visible.map(({ g, i }) => (
            <GroupCard key={i} group={g} onResolved={() => setResolved((prev) => new Set(prev).add(i))} />
          ))}
        </>
      )}
    </div>
  )
}
