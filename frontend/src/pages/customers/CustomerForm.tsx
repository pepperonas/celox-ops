import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getCustomer, createCustomer, updateCustomer } from '../../api/customers'
import type { CustomerCreate } from '../../types'

const emptyForm: CustomerCreate = {
  name: '',
  firma: '',
  email: '',
  telefon: '',
  adresse: '',
  plz: '',
  ort: '',
  land: 'Deutschland',
  notizen: '',
}

export default function CustomerForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<CustomerCreate>(emptyForm)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      getCustomer(Number(id)).then((c) =>
        setForm({
          name: c.name,
          firma: c.firma,
          email: c.email,
          telefon: c.telefon,
          adresse: c.adresse,
          plz: c.plz,
          ort: c.ort,
          land: c.land,
          notizen: c.notizen,
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
        await updateCustomer(Number(id), form)
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
      <h2 className="text-2xl font-bold text-gray-100 mb-6">
        {isEdit ? 'Kunde bearbeiten' : 'Neuer Kunde'}
      </h2>

      <form onSubmit={handleSubmit} className="card space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Name" name="name" value={form.name || ''} onChange={handleChange} required />
          <FormField label="Firma" name="firma" value={form.firma || ''} onChange={handleChange} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="E-Mail" name="email" type="email" value={form.email || ''} onChange={handleChange} />
          <FormField label="Telefon" name="telefon" type="tel" value={form.telefon || ''} onChange={handleChange} />
        </div>
        <FormField label="Adresse" name="adresse" value={form.adresse || ''} onChange={handleChange} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField label="PLZ" name="plz" value={form.plz || ''} onChange={handleChange} />
          <FormField label="Ort" name="ort" value={form.ort || ''} onChange={handleChange} />
          <FormField label="Land" name="land" value={form.land || ''} onChange={handleChange} />
        </div>
        <FormField label="Notizen" name="notizen" type="textarea" value={form.notizen || ''} onChange={handleChange} />

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
