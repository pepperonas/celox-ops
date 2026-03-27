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
  customer_id: 0,
  titel: '',
  beschreibung: '',
  typ: 'hosting',
  status: 'aktiv',
  monatlicher_betrag: 0,
  start_datum: '',
  end_datum: '',
  auto_verlaengerung: true,
  kuendigungsfrist_tage: 30,
  notizen: '',
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
      getContract(Number(id)).then((c) =>
        setForm({
          customer_id: c.customer_id,
          titel: c.titel,
          beschreibung: c.beschreibung,
          typ: c.typ,
          status: c.status,
          monatlicher_betrag: c.monatlicher_betrag,
          start_datum: c.start_datum?.split('T')[0] || '',
          end_datum: c.end_datum?.split('T')[0] || '',
          auto_verlaengerung: c.auto_verlaengerung,
          kuendigungsfrist_tage: c.kuendigungsfrist_tage,
          notizen: c.notizen,
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
        await updateContract(Number(id), form)
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Typ"
            name="typ"
            type="select"
            value={form.typ}
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
          name="monatlicher_betrag"
          type="number"
          value={form.monatlicher_betrag || 0}
          onChange={handleChange}
          step="0.01"
          min={0}
        />
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Automatische Verlaengerung"
            name="auto_verlaengerung"
            type="checkbox"
            value={form.auto_verlaengerung ?? true}
            onChange={handleChange}
          />
          <FormField
            label="Kuendigungsfrist (Tage)"
            name="kuendigungsfrist_tage"
            type="number"
            value={form.kuendigungsfrist_tage || 30}
            onChange={handleChange}
            min={0}
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
