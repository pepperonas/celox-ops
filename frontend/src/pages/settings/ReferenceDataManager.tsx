import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import Select from '../../components/Select'
import { useAuthStore } from '../../store/authStore'
import { canDelete } from '../../utils/permissions'
import { invalidateSuggestions } from '../../api/suggestions'
import {
  createRefValue, deleteRefValue, getRefFields, getRefValues, renameRefValue,
  type RefField, type RefValue,
} from '../../api/referenceValues'

/**
 * Zentrale Verwaltung feldbezogener Referenzwerte/Tags (Phase B2). Werte je Feld
 * ansehen (mit Verwendungszähler + Quelle), anlegen, umbenennen (global auf alle
 * Datensätze propagiert) und löschen (optional durch anderen Wert ersetzen).
 * Umbenennen/Löschen sind für die Rolle „Mitarbeiter“ serverseitig gesperrt und
 * hier ausgeblendet. Modals portalen an document.body (Transform-Ancestor-Regel).
 */
export default function ReferenceDataManager() {
  const role = useAuthStore((s) => s.role)
  const mayManage = canDelete(role)

  const [fields, setFields] = useState<RefField[]>([])
  const [field, setField] = useState('tag')
  const [values, setValues] = useState<RefValue[]>([])
  const [loading, setLoading] = useState(false)
  const [q, setQ] = useState('')
  const [newValue, setNewValue] = useState('')
  const [renaming, setRenaming] = useState<RefValue | null>(null)
  const [deleting, setDeleting] = useState<RefValue | null>(null)

  useEffect(() => { getRefFields().then(setFields).catch(() => {}) }, [])

  const load = useCallback(async (f: string) => {
    setLoading(true)
    try { setValues(await getRefValues(f)) }
    catch { toast.error('Werte konnten nicht geladen werden.') }
    setLoading(false)
  }, [])

  useEffect(() => { load(field) }, [field, load])

  const afterChange = () => { invalidateSuggestions(field); load(field) }

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase()
    return qq ? values.filter((v) => v.value.toLowerCase().includes(qq)) : values
  }, [values, q])

  const label = fields.find((f) => f.key === field)?.label ?? field

  const addValue = async () => {
    const v = newValue.trim()
    if (!v) return
    try {
      await createRefValue(field, v)
      setNewValue('')
      toast.success(`„${v}“ angelegt.`)
      afterChange()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Anlegen fehlgeschlagen.')
    }
  }

  return (
    <div className="bg-surface border border-border rounded-card p-5 mb-6">
      <h3 className="text-sm font-semibold text-text mb-1">Werte &amp; Tags verwalten</h3>
      <p className="text-text-muted text-sm mb-4">
        Feldbezogene Auswahlwerte ansehen, anlegen, umbenennen oder löschen.
        Umbenennen/Löschen wird auf <strong>alle</strong> Datensätze angewandt.
      </p>

      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="min-w-[220px]">
          <label className="block text-xs text-text-muted mb-1">Feld</label>
          <Select
            value={field}
            onChange={(e) => { setField(e.target.value); setQ('') }}
            options={fields.map((f) => ({ value: f.key, label: f.label }))}
            aria-label="Feld"
          />
        </div>
        <div className="flex-1 min-w-[180px]">
          <label htmlFor="rv-search" className="block text-xs text-text-muted mb-1">Suchen</label>
          <input id="rv-search" value={q} onChange={(e) => setQ(e.target.value)}
                 className="w-full" placeholder={`In ${label} suchen…`} />
        </div>
      </div>

      {mayManage && (
        <div className="flex items-end gap-2 mb-4">
          <div className="flex-1">
            <label htmlFor="rv-new" className="block text-xs text-text-muted mb-1">Neuen Wert anlegen</label>
            <input id="rv-new" value={newValue} onChange={(e) => setNewValue(e.target.value)}
                   onKeyDown={(e) => { if (e.key === 'Enter') addValue() }}
                   className="w-full" placeholder="z. B. neue Quelle / Rolle / Tag…" />
          </div>
          <button onClick={addValue} disabled={!newValue.trim()} className="btn-secondary text-sm">Anlegen</button>
        </div>
      )}

      {loading ? (
        <div className="py-8 text-center text-text-muted text-sm">Lädt…</div>
      ) : filtered.length === 0 ? (
        <div className="py-8 text-center text-text-muted text-sm">Keine Werte.</div>
      ) : (
        <div className="max-h-[420px] overflow-y-auto -mx-1 px-1">
          <ul className="divide-y divide-border">
            {filtered.map((v) => {
              const manageable = mayManage && (v.custom || v.count > 0)
              return (
                <li key={v.value} className="flex items-center gap-2 py-2">
                  <span className="flex-1 min-w-0 truncate text-sm text-text" title={v.value}>{v.value}</span>
                  <span className={`shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    v.custom ? 'bg-[#e0a500]/15 text-[#e0a500]' : 'bg-surface-container text-text-muted'
                  }`}>{v.custom ? 'Eigen' : 'Standard'}</span>
                  <span className="shrink-0 text-xs text-text-muted tabular-nums w-16 text-right"
                        title={`${v.count} Verwendungen`}>{v.count}×</span>
                  <div className="shrink-0 flex gap-1 w-[92px] justify-end">
                    {manageable && (
                      <>
                        <button onClick={() => setRenaming(v)} title="Umbenennen"
                                className="w-8 h-8 grid place-items-center rounded-md md-state text-text-muted hover:text-text">✏️</button>
                        <button onClick={() => setDeleting(v)} title="Löschen"
                                className="w-8 h-8 grid place-items-center rounded-md md-state text-danger">🗑️</button>
                      </>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {renaming && (
        <RenameModal field={field} item={renaming}
          onClose={() => setRenaming(null)}
          onDone={() => { setRenaming(null); afterChange() }} />
      )}
      {deleting && (
        <DeleteModal field={field} item={deleting} others={values}
          onClose={() => setDeleting(null)}
          onDone={() => { setDeleting(null); afterChange() }} />
      )}
    </div>
  )
}

function RenameModal({ field, item, onClose, onDone }: {
  field: string; item: RefValue; onClose: () => void; onDone: () => void
}) {
  const [value, setValue] = useState(item.value)
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    const v = value.trim()
    if (!v || v === item.value) { onClose(); return }
    setBusy(true)
    try {
      const r = await renameRefValue(field, item.value, v)
      toast.success(`Umbenannt → „${r.value}“ (${r.affected} Datensätze aktualisiert).`)
      onDone()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Umbenennen fehlgeschlagen.')
      setBusy(false)
    }
  }
  return createPortal(
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => !busy && onClose()}>
      <div className="bg-surface border border-border rounded-dialog p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-text mb-3">Wert umbenennen</h3>
        <p className="text-xs text-text-muted mb-3">
          „{item.value}“ wird in <strong>{item.count}</strong> Datensätzen ersetzt.
        </p>
        <input value={value} onChange={(e) => setValue(e.target.value)} autoFocus
               onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
               className="w-full mb-4" />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={busy} className="btn-secondary">Abbrechen</button>
          <button onClick={submit} disabled={busy} className="btn-primary">{busy ? 'Speichere…' : 'Umbenennen'}</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

function DeleteModal({ field, item, others, onClose, onDone }: {
  field: string; item: RefValue; others: RefValue[]; onClose: () => void; onDone: () => void
}) {
  const [replace, setReplace] = useState('')
  const [busy, setBusy] = useState(false)
  const options = others
    .filter((o) => o.value !== item.value)
    .map((o) => ({ value: o.value, label: o.value }))
  const submit = async () => {
    setBusy(true)
    try {
      const r = await deleteRefValue(field, item.value, replace || null)
      toast.success(replace
        ? `Ersetzt durch „${r.replaced}“ (${r.affected} Datensätze).`
        : `Gelöscht (aus ${r.affected} Datensätzen entfernt).`)
      onDone()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Löschen fehlgeschlagen.')
      setBusy(false)
    }
  }
  return createPortal(
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => !busy && onClose()}>
      <div className="bg-surface border border-border rounded-dialog p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-text mb-2">Wert löschen</h3>
        <p className="text-sm text-text mb-3">
          „{item.value}“ wird aus <strong>{item.count}</strong> Datensätzen entfernt. Kein Undo.
        </p>
        <label className="block text-xs text-text-muted mb-1">Stattdessen ersetzen durch (optional)</label>
        <Select value={replace} onChange={(e) => setReplace(e.target.value)}
                placeholder="— ersatzlos entfernen —" options={options} aria-label="Ersatzwert" />
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} disabled={busy} className="btn-secondary">Abbrechen</button>
          <button onClick={submit} disabled={busy} className="btn-primary !bg-danger !text-white">
            {busy ? 'Lösche…' : replace ? 'Ersetzen' : 'Löschen'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
