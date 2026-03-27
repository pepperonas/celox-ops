import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getCustomer, createCustomer, updateCustomer } from '../../api/customers'
import type { CustomerCreate } from '../../types'

const emptyForm: CustomerCreate = {
  name: '',
  company: '',
  email: '',
  phone: '',
  address: '',
  website: '',
  token_tracker_url: '',
  notes: '',
}

export default function CustomerForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<CustomerCreate>(emptyForm)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      getCustomer(id).then((c) =>
        setForm({
          name: c.name,
          company: c.company,
          email: c.email,
          phone: c.phone,
          address: c.address,
          website: c.website,
          token_tracker_url: c.token_tracker_url,
          notes: c.notes,
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
        await updateCustomer(id!, form)
        toast.success('Kunde aktualisiert.')
        navigate(`/kunden/${id}`)
      } else {
        const created = await createCustomer(form)
        toast.success('Kunde erstellt.')
        navigate(`/kunden/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Kunde bearbeiten' : 'Neuer Kunde'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Name" name="name" value={form.name || ''} onChange={handleChange} required />
          <FormField label="Firma" name="company" value={form.company || ''} onChange={handleChange} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="E-Mail" name="email" type="email" value={form.email || ''} onChange={handleChange} />
          <FormField label="Telefon" name="phone" type="tel" value={form.phone || ''} onChange={handleChange} />
        </div>
        <FormField label="Website" name="website" value={form.website || ''} onChange={handleChange} placeholder="https://example.de" />
        <FormField label="Token Tracker URL" name="token_tracker_url" value={form.token_tracker_url || ''} onChange={handleChange} placeholder="https://tracker.example.com/api/public/share/..." />
        <FormField label="Adresse" name="address" value={form.address || ''} onChange={handleChange} />
        <FormField label="Notizen" name="notes" type="textarea" value={form.notes || ''} onChange={handleChange} />

        <div className="flex justify-end gap-3 pt-4">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
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
