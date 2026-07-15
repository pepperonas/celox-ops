import { useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import type {
  OutreachCategory,
  OutreachChannel,
  OutreachTemplate,
  OutreachTemplateCreate,
} from '../../types'
import { createOutreachTemplate, updateOutreachTemplate } from '../../api/outreach'
import { CATEGORIES, CHANNELS, PLACEHOLDERS } from './constants'

interface Props {
  template?: OutreachTemplate | null   // gesetzt = Bearbeiten
  initialChannel?: OutreachChannel
  onClose: () => void
  onSaved: (t: OutreachTemplate) => void
}

export default function TemplateFormModal({ template, initialChannel, onClose, onSaved }: Props) {
  const isEdit = Boolean(template)
  const [channel, setChannel] = useState<OutreachChannel>(template?.channel || initialChannel || 'email')
  const [category, setCategory] = useState<OutreachCategory>(template?.category || 'kaltakquise')
  const [title, setTitle] = useState(template?.title || '')
  const [subject, setSubject] = useState(template?.subject || '')
  const [body, setBody] = useState(template?.body || '')
  const [notes, setNotes] = useState(template?.notes || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!title.trim() || !body.trim()) {
      toast.error('Titel und Body sind Pflicht.')
      return
    }
    setSaving(true)
    const payload: OutreachTemplateCreate = {
      channel,
      category,
      title: title.trim(),
      subject: channel === 'email' ? (subject.trim() || null) : null,
      body: body.trim(),
      notes: notes.trim() || null,
    }
    try {
      const saved = isEdit
        ? await updateOutreachTemplate(template!.id, payload)
        : await createOutreachTemplate(payload)
      toast.success(isEdit ? 'Template aktualisiert.' : 'Template angelegt.')
      onSaved(saved)
    } catch {
      toast.error('Speichern fehlgeschlagen.')
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade p-4">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-6 max-w-[680px] w-full max-h-[90vh] flex flex-col animate-modal-in">
        <h3 className="text-lg font-semibold text-text mb-4">{isEdit ? 'Template bearbeiten' : 'Neues Template'}</h3>

        <div className="flex-1 min-h-0 overflow-y-auto space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Kanal</label>
              <select value={channel} onChange={(e) => setChannel(e.target.value as OutreachChannel)} className="w-full">
                {CHANNELS.map((c) => <option key={c.value} value={c.value}>{c.icon} {c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Rubrik</label>
              <select value={category} onChange={(e) => setCategory(e.target.value as OutreachCategory)} className="w-full">
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1.5">Titel</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full" placeholder="Kurzer sprechender Name" />
          </div>

          {channel === 'email' && (
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Betreff</label>
              <input value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full" placeholder="{{firma}}: …" />
            </div>
          )}

          <div>
            <label className="block text-xs text-text-muted mb-1.5">
              Body{channel === 'phone' && ' (Abschnitte mit ## Einstieg / ## Nutzenargument / ## Einwandbehandlung / ## Abschluss)'}
            </label>
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={channel === 'phone' ? 12 : 7}
                      className="w-full resize-y font-sans" placeholder="Text mit {{platzhaltern}}…" />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1.5">Interne Notiz (optional)</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full" placeholder="z. B. bei Erstkontakt max. 5 Sätze" />
          </div>

          <div className="rounded-lg bg-surface-container border border-border p-3">
            <p className="text-xs text-text-muted mb-1.5">Verfügbare Platzhalter (Klick zum Anhängen an den Body):</p>
            <div className="flex flex-wrap gap-1.5">
              {PLACEHOLDERS.map((p) => (
                <button key={p.key} type="button" onClick={() => setBody((b) => `${b}{{${p.key}}}`)}
                        title={p.example}
                        className="text-[11px] px-2 py-1 rounded-full bg-surface-high border border-border text-text-muted hover:text-text">
                  {`{{${p.key}}}`}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4 mt-2 border-t border-border">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>Abbrechen</button>
          <button onClick={save} className="btn-primary" disabled={saving}>{saving ? 'Speichern…' : 'Speichern'}</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
