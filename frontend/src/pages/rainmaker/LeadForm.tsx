import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import PageHeader from '../../components/PageHeader'
import { getRainmakerLead, createRainmakerLead, updateRainmakerLead } from '../../api/rainmaker'
import type { RainmakerLeadCreate, RainmakerLeadStatus, RainmakerPriority } from '../../types'
import { useFormShortcuts } from '../../hooks/useFormShortcuts'
import { STATUS_LABELS, PRIORITY_LABELS } from './constants'

const statusOptions = (Object.keys(STATUS_LABELS) as RainmakerLeadStatus[]).map((v) => ({
  value: v,
  label: STATUS_LABELS[v],
}))
const priorityOptions = (Object.keys(PRIORITY_LABELS) as RainmakerPriority[]).map((v) => ({
  value: v,
  label: PRIORITY_LABELS[v],
}))

const emptyForm: RainmakerLeadCreate = {
  company: '',
  contact_name: '',
  role: '',
  phone: '',
  email: '',
  website: '',
  address: '',
  source: '',
  status: 'new',
  priority: 'medium',
  value_estimate: null,
  tags: [],
  notes: '',
}

export default function RainmakerLeadForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<RainmakerLeadCreate>(emptyForm)
  const [tagsInput, setTagsInput] = useState('')
  const [valueInput, setValueInput] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    getRainmakerLead(id).then((l) => {
      setForm({
        company: l.company,
        contact_name: l.contact_name ?? '',
        role: l.role ?? '',
        phone: l.phone ?? '',
        email: l.email ?? '',
        website: l.website ?? '',
        address: l.address ?? '',
        source: l.source ?? '',
        status: l.status,
        priority: l.priority,
        value_estimate: l.value_estimate,
        tags: l.tags ?? [],
        notes: l.notes ?? '',
      })
      setTagsInput((l.tags ?? []).join(', '))
      setValueInput(l.value_estimate != null ? String(l.value_estimate) : '')
    }).catch(() => toast.error('Lead konnte nicht geladen werden.'))
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  useFormShortcuts({
    onSubmit: () => {
      if (loading) return
      const formEl = document.querySelector('form') as HTMLFormElement | null
      formEl?.requestSubmit()
    },
    onCancel: () => navigate(-1),
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    const payload: RainmakerLeadCreate = {
      ...form,
      value_estimate: valueInput.trim() ? Number(valueInput.replace(',', '.')) : null,
      tags: tagsInput.split(',').map((t) => t.trim()).filter(Boolean),
    }
    try {
      if (isEdit) {
        await updateRainmakerLead(id!, payload)
        toast.success('Lead aktualisiert.')
        navigate(`/pipeline/leads/${id}`)
      } else {
        let created
        try {
          created = await createRainmakerLead(payload)
        } catch (err: unknown) {
          const resp = (err as { response?: { status?: number; data?: { detail?: { message?: string } } } })?.response
          // 409 = ähnlicher Lead existiert → nachfragen, dann ggf. mit force anlegen
          if (resp?.status === 409) {
            const msg = resp.data?.detail?.message || 'Ähnlicher Lead existiert bereits. Trotzdem anlegen?'
            if (!window.confirm(msg)) { setLoading(false); return }
            created = await createRainmakerLead(payload, true)
          } else {
            throw err
          }
        }
        toast.success('Lead erstellt.')
        navigate(`/pipeline/leads/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-3xl">
      <PageHeader title={isEdit ? 'Lead bearbeiten' : 'Neuer Lead'} />

      <form onSubmit={handleSubmit} className="bg-surface-container border border-border rounded-card p-6 space-y-5">
        <FormField label="Firma" name="company" value={form.company} onChange={handleChange} required placeholder="Firmenname" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Ansprechpartner" name="contact_name" value={form.contact_name ?? ''} onChange={handleChange} placeholder="Name" />
          <FormField label="Funktion" name="role" value={form.role ?? ''} onChange={handleChange} placeholder="z. B. Geschäftsführer" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Telefon" name="phone" type="tel" value={form.phone ?? ''} onChange={handleChange} placeholder="0123 / 456789" />
          <FormField label="E-Mail" name="email" type="email" value={form.email ?? ''} onChange={handleChange} placeholder="info@example.de" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Website" name="website" value={form.website ?? ''} onChange={handleChange} placeholder="https://example.de" />
          <FormField label="Quelle" name="source" value={form.source ?? ''} onChange={handleChange} placeholder="Empfehlung, Messe, Recherche…" />
        </div>

        <FormField label="Adresse" name="address" type="textarea" value={form.address ?? ''} onChange={handleChange} placeholder="Straße, PLZ Ort" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField label="Status" name="status" type="select" value={form.status ?? 'new'} onChange={handleChange} options={statusOptions} />
          <FormField label="Priorität" name="priority" type="select" value={form.priority ?? 'medium'} onChange={handleChange} options={priorityOptions} />
          <div>
            <label className="block text-xs text-text-muted mb-2">Geschätzter Wert (€)</label>
            <input type="number" step="0.01" min="0" value={valueInput} onChange={(e) => setValueInput(e.target.value)} className="w-full" placeholder="z. B. 2500" />
          </div>
        </div>

        <div>
          <label className="block text-xs text-text-muted mb-2">Tags (kommagetrennt)</label>
          <input type="text" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} className="w-full" placeholder="Webshop, lokal, Bestandskunde" />
        </div>

        <FormField label="Notizen" name="notes" type="textarea" value={form.notes ?? ''} onChange={handleChange} placeholder="Kontext, Gesprächsnotizen…" />

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Abbrechen</button>
          <button type="submit" disabled={loading} className="btn-primary" title="Ctrl+S / ⌘S">
            {loading ? 'Speichern…' : 'Speichern'}
          </button>
        </div>
      </form>
    </div>
  )
}
