import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getOrder, createOrder, updateOrder } from '../../api/orders'
import { getCustomers } from '../../api/customers'
import type { OrderCreate, Customer } from '../../types'

const statusOptions = [
  { value: 'angebot', label: 'Angebot' },
  { value: 'beauftragt', label: 'Beauftragt' },
  { value: 'in_arbeit', label: 'In Arbeit' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
  { value: 'storniert', label: 'Storniert' },
]

const emptyForm: OrderCreate = {
  customer_id: 0,
  titel: '',
  beschreibung: '',
  status: 'angebot',
  betrag: 0,
  stundensatz: 0,
  start_datum: '',
  end_datum: '',
  notizen: '',
}

export default function OrderForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<OrderCreate>(emptyForm)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getCustomers({ page_size: 1000 }).then((r) => setCustomers(r.items))
    if (id) {
      getOrder(Number(id)).then((o) =>
        setForm({
          customer_id: o.customer_id,
          titel: o.titel,
          beschreibung: o.beschreibung,
          status: o.status,
          betrag: o.betrag,
          stundensatz: o.stundensatz,
          start_datum: o.start_datum?.split('T')[0] || '',
          end_datum: o.end_datum?.split('T')[0] || '',
          notizen: o.notizen,
        }),
      )
    }
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value, type } = e.target
    setForm({
      ...form,
      [name]: type === 'number' ? parseFloat(value) || 0 : value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateOrder(Number(id), form)
        toast.success('Auftrag aktualisiert.')
        navigate(`/auftraege/${id}`)
      } else {
        const created = await createOrder(form)
        toast.success('Auftrag erstellt.')
        navigate(`/auftraege/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-100 mb-6">
        {isEdit ? 'Auftrag bearbeiten' : 'Neuer Auftrag'}
      </h2>

      <form onSubmit={handleSubmit} className="card space-y-4">
        <FormField
          label="Kunde"
          name="customer_id"
          type="select"
          value={form.customer_id}
          onChange={handleChange}
          required
          options={customers.map((c) => ({
            value: c.id,
            label: c.firma ? `${c.name} (${c.firma})` : c.name,
          }))}
          placeholder="Kunde waehlen..."
        />
        <FormField label="Titel" name="titel" value={form.titel} onChange={handleChange} required />
        <FormField
          label="Beschreibung"
          name="beschreibung"
          type="textarea"
          value={form.beschreibung || ''}
          onChange={handleChange}
        />
        <FormField
          label="Status"
          name="status"
          type="select"
          value={form.status || 'angebot'}
          onChange={handleChange}
          options={statusOptions}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Betrag"
            name="betrag"
            type="number"
            value={form.betrag || 0}
            onChange={handleChange}
            step="0.01"
            min={0}
          />
          <FormField
            label="Stundensatz"
            name="stundensatz"
            type="number"
            value={form.stundensatz || 0}
            onChange={handleChange}
            step="0.01"
            min={0}
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Startdatum"
            name="start_datum"
            type="date"
            value={form.start_datum || ''}
            onChange={handleChange}
          />
          <FormField
            label="Enddatum"
            name="end_datum"
            type="date"
            value={form.end_datum || ''}
            onChange={handleChange}
          />
        </div>
        <FormField
          label="Notizen"
          name="notizen"
          type="textarea"
          value={form.notizen || ''}
          onChange={handleChange}
        />

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
