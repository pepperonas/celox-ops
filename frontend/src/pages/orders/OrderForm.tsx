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
  customer_id: '',
  title: '',
  description: '',
  status: 'angebot',
  amount: 0,
  hourly_rate: 0,
  start_date: '',
  end_date: '',
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
      getOrder(id).then((o) =>
        setForm({
          customer_id: o.customer_id,
          title: o.title,
          description: o.description,
          status: o.status,
          amount: o.amount,
          hourly_rate: o.hourly_rate,
          start_date: o.start_date?.split('T')[0] || '',
          end_date: o.end_date?.split('T')[0] || '',
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
        await updateOrder(id!, form)
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
            label: c.company ? `${c.name} (${c.company})` : c.name,
          }))}
          placeholder="Kunde waehlen..."
        />
        <FormField label="Titel" name="title" value={form.title} onChange={handleChange} required />
        <FormField
          label="Beschreibung"
          name="description"
          type="textarea"
          value={form.description || ''}
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
            name="amount"
            type="number"
            value={form.amount || 0}
            onChange={handleChange}
            step="0.01"
            min={0}
          />
          <FormField
            label="Stundensatz"
            name="hourly_rate"
            type="number"
            value={form.hourly_rate || 0}
            onChange={handleChange}
            step="0.01"
            min={0}
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Startdatum"
            name="start_date"
            type="date"
            value={form.start_date || ''}
            onChange={handleChange}
          />
          <FormField
            label="Enddatum"
            name="end_date"
            type="date"
            value={form.end_date || ''}
            onChange={handleChange}
          />
        </div>

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
