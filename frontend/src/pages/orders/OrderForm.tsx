import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import AutocompleteInput from '../../components/AutocompleteInput'
import { getOrder, createOrder, updateOrder } from '../../api/orders'
import { getCustomers } from '../../api/customers'
import type { OrderCreate, Customer, InvoicePosition } from '../../types'

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
  valid_until: '',
  positions: null,
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
          valid_until: o.valid_until?.split('T')[0] || '',
          positions: o.positions || null,
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Auftrag bearbeiten' : 'Neuer Auftrag'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
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
          placeholder="Kunde wählen..."
        />
        <AutocompleteInput label="Titel" name="title" value={form.title} onChange={handleChange} required placeholder="z.B. Website-Erstellung, IT-Beratung..." />
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
        <FormField
          label="Gültig bis"
          name="valid_until"
          type="date"
          value={form.valid_until || ''}
          onChange={handleChange}
        />

        {/* Positionen */}
        <div className="border-t border-border pt-4 mt-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-text">Positionen (optional)</h3>
            <button
              type="button"
              onClick={() => {
                const positions: InvoicePosition[] = form.positions || []
                setForm({
                  ...form,
                  positions: [
                    ...positions,
                    { position: positions.length + 1, beschreibung: '', menge: 1, einheit: 'Stk', einzelpreis: 0, gesamt: 0 },
                  ],
                })
              }}
              className="btn-secondary text-xs"
            >
              + Position
            </button>
          </div>
          {form.positions && form.positions.length > 0 && (
            <div className="space-y-3">
              {form.positions.map((pos, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-4">
                    <label className="block text-xs text-text-muted mb-1">Beschreibung</label>
                    <input
                      type="text"
                      value={pos.beschreibung}
                      onChange={(e) => {
                        const updated = [...(form.positions || [])]
                        updated[idx] = { ...updated[idx], beschreibung: e.target.value }
                        setForm({ ...form, positions: updated })
                      }}
                      className="input w-full"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-text-muted mb-1">Menge</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pos.menge}
                      onChange={(e) => {
                        const updated = [...(form.positions || [])]
                        const menge = parseFloat(e.target.value) || 0
                        updated[idx] = { ...updated[idx], menge, gesamt: menge * updated[idx].einzelpreis }
                        setForm({ ...form, positions: updated })
                      }}
                      className="input w-full"
                    />
                  </div>
                  <div className="col-span-1">
                    <label className="block text-xs text-text-muted mb-1">Einheit</label>
                    <input
                      type="text"
                      value={pos.einheit}
                      onChange={(e) => {
                        const updated = [...(form.positions || [])]
                        updated[idx] = { ...updated[idx], einheit: e.target.value }
                        setForm({ ...form, positions: updated })
                      }}
                      className="input w-full"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-text-muted mb-1">Einzelpreis</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pos.einzelpreis}
                      onChange={(e) => {
                        const updated = [...(form.positions || [])]
                        const einzelpreis = parseFloat(e.target.value) || 0
                        updated[idx] = { ...updated[idx], einzelpreis, gesamt: updated[idx].menge * einzelpreis }
                        setForm({ ...form, positions: updated })
                      }}
                      className="input w-full"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-text-muted mb-1">Gesamt</label>
                    <input
                      type="number"
                      value={pos.gesamt.toFixed(2)}
                      readOnly
                      className="input w-full bg-surface-2"
                    />
                  </div>
                  <div className="col-span-1">
                    <button
                      type="button"
                      onClick={() => {
                        const updated = (form.positions || []).filter((_, i) => i !== idx).map((p, i) => ({ ...p, position: i + 1 }))
                        setForm({ ...form, positions: updated.length > 0 ? updated : null })
                      }}
                      className="text-red-500 hover:text-red-700 text-sm p-1"
                      title="Position entfernen"
                    >
                      &times;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
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
