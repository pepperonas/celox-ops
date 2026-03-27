import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { getInvoice, createInvoice, updateInvoice } from '../../api/invoices'
import { getCustomers } from '../../api/customers'
import { getOrders } from '../../api/orders'
import { getContracts } from '../../api/contracts'
import { formatCurrency } from '../../utils/formatters'
import type { InvoiceCreate, InvoicePosition, Customer, Order, Contract } from '../../types'

const emptyPosition: InvoicePosition = {
  position: 1,
  beschreibung: '',
  menge: 1,
  einheit: 'Stunden',
  einzelpreis: 0,
  gesamt: 0,
}

const emptyForm: InvoiceCreate = {
  customer_id: '',
  order_id: null,
  contract_id: null,
  title: '',
  positions: [{ ...emptyPosition }],
  tax_rate: 19,
  invoice_date: new Date().toISOString().split('T')[0],
  due_date: '',
  notes: '',
}

export default function InvoiceForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<InvoiceCreate>(emptyForm)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getCustomers({ page_size: 1000 }).then((r) => setCustomers(r.items))

    if (id) {
      getInvoice(id).then((inv) => {
        setForm({
          customer_id: inv.customer_id,
          order_id: inv.order_id,
          contract_id: inv.contract_id,
          title: inv.title,
          positions: inv.positions.length > 0 ? inv.positions : [{ ...emptyPosition }],
          tax_rate: inv.tax_rate,
          invoice_date: inv.invoice_date?.split('T')[0] || '',
          due_date: inv.due_date?.split('T')[0] || '',
          notes: inv.notes,
        })
        // Load orders/contracts for this customer
        if (inv.customer_id) {
          getOrders({ customer_id: inv.customer_id, page_size: 1000 }).then((r) => setOrders(r.items))
          getContracts({ customer_id: inv.customer_id, page_size: 1000 }).then((r) => setContracts(r.items))
        }
      })
    }
  }, [id])

  // Load orders/contracts when customer changes
  useEffect(() => {
    if (form.customer_id) {
      getOrders({ customer_id: form.customer_id, page_size: 1000 }).then((r) => setOrders(r.items))
      getContracts({ customer_id: form.customer_id, page_size: 1000 }).then((r) => setContracts(r.items))
    } else {
      setOrders([])
      setContracts([])
    }
  }, [form.customer_id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value, type } = e.target
    if (name === 'customer_id' || name === 'order_id' || name === 'contract_id') {
      const strVal = value || null
      setForm({ ...form, [name]: strVal || (name === 'customer_id' ? '' : null) })
    } else if (type === 'number') {
      setForm({ ...form, [name]: parseFloat(value) || 0 })
    } else {
      setForm({ ...form, [name]: value })
    }
  }

  const updatePosition = (index: number, field: keyof InvoicePosition, value: string | number) => {
    const updated = [...form.positions]
    const pos = { ...updated[index], [field]: value }
    pos.gesamt = pos.menge * pos.einzelpreis
    updated[index] = pos
    setForm({ ...form, positions: updated })
  }

  const addPosition = () => {
    const nextPos = form.positions.length + 1
    setForm({ ...form, positions: [...form.positions, { ...emptyPosition, position: nextPos }] })
  }

  const removePosition = (index: number) => {
    if (form.positions.length <= 1) return
    const updated = form.positions.filter((_, i) => i !== index).map((p, i) => ({ ...p, position: i + 1 }))
    setForm({ ...form, positions: updated })
  }

  const netto = form.positions.reduce((sum, p) => sum + p.menge * p.einzelpreis, 0)
  const taxRate = form.tax_rate || 0
  const taxAmount = netto * (taxRate / 100)
  const brutto = netto + taxAmount

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    const payload: InvoiceCreate = {
      ...form,
      positions: form.positions.map((p, i) => ({
        ...p,
        position: i + 1,
        gesamt: p.menge * p.einzelpreis,
      })),
    }

    try {
      if (isEdit) {
        await updateInvoice(id!, payload)
        toast.success('Rechnung aktualisiert.')
        navigate(`/rechnungen/${id}`)
      } else {
        const created = await createInvoice(payload)
        toast.success('Rechnung erstellt.')
        navigate(`/rechnungen/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-bold text-gray-100 mb-6">
        {isEdit ? 'Rechnung bearbeiten' : 'Neue Rechnung'}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="card space-y-4">
          <h3 className="text-lg font-semibold text-gray-200">Allgemein</h3>

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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="Auftrag (optional)"
              name="order_id"
              type="select"
              value={form.order_id || ''}
              onChange={handleChange}
              options={orders.map((o) => ({ value: o.id, label: o.title }))}
              placeholder="Kein Auftrag"
            />
            <FormField
              label="Vertrag (optional)"
              name="contract_id"
              type="select"
              value={form.contract_id || ''}
              onChange={handleChange}
              options={contracts.map((c) => ({ value: c.id, label: c.title }))}
              placeholder="Kein Vertrag"
            />
          </div>

          <FormField label="Titel" name="title" value={form.title} onChange={handleChange} required />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="Rechnungsdatum"
              name="invoice_date"
              type="date"
              value={form.invoice_date || ''}
              onChange={handleChange}
            />
            <FormField
              label="Faelligkeitsdatum"
              name="due_date"
              type="date"
              value={form.due_date || ''}
              onChange={handleChange}
            />
          </div>
        </div>

        {/* Positions */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-200">Positionen</h3>
            <button type="button" onClick={addPosition} className="btn-secondary text-sm">
              Position hinzufuegen
            </button>
          </div>

          <div className="space-y-3">
            {/* Header */}
            <div className="hidden md:grid md:grid-cols-12 gap-2 text-xs font-semibold text-gray-400 uppercase px-1">
              <div className="col-span-4">Beschreibung</div>
              <div className="col-span-2">Menge</div>
              <div className="col-span-2">Einheit</div>
              <div className="col-span-2">Einzelpreis</div>
              <div className="col-span-1">Gesamt</div>
              <div className="col-span-1"></div>
            </div>

            {form.positions.map((pos, idx) => (
              <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 items-start bg-gray-800/30 rounded-lg p-2 md:p-0 md:bg-transparent">
                <div className="md:col-span-4">
                  <label className="md:hidden text-xs text-gray-500 mb-1 block">Beschreibung</label>
                  <input
                    type="text"
                    value={pos.beschreibung}
                    onChange={(e) => updatePosition(idx, 'beschreibung', e.target.value)}
                    placeholder="Beschreibung"
                    className="input-field text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="md:hidden text-xs text-gray-500 mb-1 block">Menge</label>
                  <input
                    type="number"
                    value={pos.menge}
                    onChange={(e) => updatePosition(idx, 'menge', parseFloat(e.target.value) || 0)}
                    step="0.01"
                    min="0"
                    className="input-field text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="md:hidden text-xs text-gray-500 mb-1 block">Einheit</label>
                  <input
                    type="text"
                    value={pos.einheit}
                    onChange={(e) => updatePosition(idx, 'einheit', e.target.value)}
                    placeholder="Stunden"
                    className="input-field text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="md:hidden text-xs text-gray-500 mb-1 block">Einzelpreis</label>
                  <input
                    type="number"
                    value={pos.einzelpreis}
                    onChange={(e) => updatePosition(idx, 'einzelpreis', parseFloat(e.target.value) || 0)}
                    step="0.01"
                    min="0"
                    className="input-field text-sm"
                  />
                </div>
                <div className="md:col-span-1 flex items-center">
                  <label className="md:hidden text-xs text-gray-500 mb-1 block mr-2">Gesamt</label>
                  <span className="text-sm text-gray-300 py-2">
                    {formatCurrency(pos.menge * pos.einzelpreis)}
                  </span>
                </div>
                <div className="md:col-span-1 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => removePosition(idx)}
                    disabled={form.positions.length <= 1}
                    className="p-1.5 text-gray-500 hover:text-red-400 disabled:opacity-30 transition-colors"
                    title="Position entfernen"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Totals */}
          <div className="mt-6 pt-4 border-t border-gray-800">
            <div className="flex items-center gap-3 mb-4">
              <label className="text-sm text-gray-300">USt.-Satz (%):</label>
              <input
                type="number"
                name="tax_rate"
                value={form.tax_rate || 0}
                onChange={handleChange}
                step="0.01"
                min="0"
                className="input-field w-24 text-sm"
              />
            </div>

            <div className="flex flex-col items-end gap-1">
              <div className="flex justify-between w-60">
                <span className="text-sm text-gray-400">Netto:</span>
                <span className="text-sm text-gray-200 font-medium">{formatCurrency(netto)}</span>
              </div>
              <div className="flex justify-between w-60">
                <span className="text-sm text-gray-400">USt. ({taxRate}%):</span>
                <span className="text-sm text-gray-200 font-medium">{formatCurrency(taxAmount)}</span>
              </div>
              <div className="flex justify-between w-60 pt-2 border-t border-gray-700">
                <span className="text-sm font-semibold text-gray-200">Brutto:</span>
                <span className="text-sm font-bold text-celox-400">{formatCurrency(brutto)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="card">
          <FormField
            label="Notizen"
            name="notes"
            type="textarea"
            value={form.notes || ''}
            onChange={handleChange}
            placeholder="Optionale Anmerkungen zur Rechnung..."
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
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
