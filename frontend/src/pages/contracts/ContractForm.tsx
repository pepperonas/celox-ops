import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getContract, createContract, updateContract } from '../../api/contracts'
import { getCustomers } from '../../api/customers'
import type { ContractCreate, Customer } from '../../types'

const typeOptions = [
  { value: 'hosting', label: 'Hosting' },
  { value: 'wartung', label: 'Wartung' },
  { value: 'support', label: 'Support' },
  { value: 'sonstige', label: 'Sonstige' },
]

const statusOptions = [
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'gekuendigt', label: 'Gekuendigt' },
  { value: 'ausgelaufen', label: 'Ausgelaufen' },
]

const emptyForm: ContractCreate = {
  customer_id: '',
  title: '',
  description: '',
  type: 'hosting',
  status: 'aktiv',
  monthly_amount: 0,
  start_date: '',
  end_date: '',
  auto_renew: true,
  notice_period_days: 30,
}

export default function ContractForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<ContractCreate>(emptyForm)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getCustomers({ page_size: 1000 }).then((r) => setCustomers(r.items))
    if (id) {
      getContract(id).then((c) =>
        setForm({
          customer_id: c.customer_id,
          title: c.title,
          description: c.description,
          type: c.type,
          status: c.status,
          monthly_amount: c.monthly_amount,
          start_date: c.start_date?.split('T')[0] || '',
          end_date: c.end_date?.split('T')[0] || '',
          auto_renew: c.auto_renew,
          notice_period_days: c.notice_period_days,
        }),
      )
    }
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value, type } = e.target
    if (type === 'checkbox') {
      setForm({ ...form, [name]: (e.target as HTMLInputElement).checked })
    } else {
      setForm({
        ...form,
        [name]: type === 'number' ? parseFloat(value) || 0 : value,
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateContract(id!, form)
        toast.success('Vertrag aktualisiert.')
        navigate(`/vertraege/${id}`)
      } else {
        const created = await createContract(form)
        toast.success('Vertrag erstellt.')
        navigate(`/vertraege/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-100 mb-6">
        {isEdit ? 'Vertrag bearbeiten' : 'Neuer Vertrag'}
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Typ"
            name="type"
            type="select"
            value={form.type}
            onChange={handleChange}
            options={typeOptions}
          />
          <FormField
            label="Status"
            name="status"
            type="select"
            value={form.status || 'aktiv'}
            onChange={handleChange}
            options={statusOptions}
          />
        </div>
        <FormField
          label="Monatlicher Betrag"
          name="monthly_amount"
          type="number"
          value={form.monthly_amount || 0}
          onChange={handleChange}
          step="0.01"
          min={0}
        />
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Automatische Verlaengerung"
            name="auto_renew"
            type="checkbox"
            value={form.auto_renew ?? true}
            onChange={handleChange}
          />
          <FormField
            label="Kuendigungsfrist (Tage)"
            name="notice_period_days"
            type="number"
            value={form.notice_period_days || 30}
            onChange={handleChange}
            min={0}
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
