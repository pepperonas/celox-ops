import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getLead, createLead, updateLead } from '../../api/leads'
import type { LeadCreate } from '../../types'

const statusOptions = [
  { value: 'neu', label: 'Neu' },
  { value: 'kontaktiert', label: 'Kontaktiert' },
  { value: 'interessiert', label: 'Interessiert' },
  { value: 'abgelehnt', label: 'Abgelehnt' },
]

const emptyForm: LeadCreate = {
  url: '',
  name: '',
  company: '',
  email: '',
  phone: '',
  notes: '',
  status: 'neu',
}

export default function LeadForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<LeadCreate>(emptyForm)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      getLead(id).then((l) =>
        setForm({
          url: l.url,
          name: l.name,
          company: l.company,
          email: l.email,
          phone: l.phone,
          notes: l.notes,
          status: l.status,
        }),
      )
    }
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateLead(id!, form)
        toast.success('Lead aktualisiert.')
      } else {
        await createLead(form)
        toast.success('Lead erstellt.')
      }
      navigate('/vorgemerkt')
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Lead bearbeiten' : 'Neue Website vormerken'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
        <FormField
          label="URL"
          name="url"
          value={form.url || ''}
          onChange={handleChange}
          required
          placeholder="https://example.de"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Name" name="name" value={form.name || ''} onChange={handleChange} />
          <FormField label="Firma" name="company" value={form.company || ''} onChange={handleChange} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="E-Mail" name="email" type="email" value={form.email || ''} onChange={handleChange} />
          <FormField label="Telefon" name="phone" type="tel" value={form.phone || ''} onChange={handleChange} />
        </div>
        <FormField
          label="Status"
          name="status"
          type="select"
          value={form.status || 'neu'}
          onChange={handleChange}
          options={statusOptions}
        />
        <FormField label="Notizen" name="notes" type="textarea" value={form.notes || ''} onChange={handleChange} placeholder="Was ist an der Website verbesserungswuerdig..." />

        <div className="flex justify-end gap-3 pt-4">
          <button type="button" onClick={() => navigate('/vorgemerkt')} className="btn-secondary">
            Abbrechen
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Speichern...' : 'Speichern'}
          </button>
        </div>
      </form>
    </div>
  )
}
