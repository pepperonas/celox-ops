import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import axios from 'axios'
import FormField from '../../components/FormField'
import AutocompleteInput, { POSITION_SUGGESTIONS } from '../../components/AutocompleteInput'
import { getInvoice, createInvoice, updateInvoice } from '../../api/invoices'
import { getCustomers, getCustomer } from '../../api/customers'
import { getOrders } from '../../api/orders'
import { getContracts } from '../../api/contracts'
import { formatCurrency } from '../../utils/formatters'
import type { InvoiceCreate, InvoicePosition, Customer, Order, Contract, TokenTrackerData } from '../../types'

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
  due_date: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0],
  notes: '',
  token_usage_from: null,
  token_usage_to: null,
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
  const [attachTokenUsage, setAttachTokenUsage] = useState(false)
  const [selectedCustomerHasTracker, setSelectedCustomerHasTracker] = useState(false)
  const [selectedCustomerTrackerUrl, setSelectedCustomerTrackerUrl] = useState('')
  const [discountEnabled, setDiscountEnabled] = useState(false)
  const [discountPercent, setDiscountPercent] = useState(true)
  const [discountValue, setDiscountValue] = useState('')
  const [discountReason, setDiscountReason] = useState('')
  const [showAiImport, setShowAiImport] = useState(false)
  const [aiImportFrom, setAiImportFrom] = useState('')
  const [aiImportTo, setAiImportTo] = useState(new Date().toISOString().split('T')[0])
  const [aiHourlyRate, setAiHourlyRate] = useState(95)
  const [aiImportLoading, setAiImportLoading] = useState(false)

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

  // Load orders/contracts and check tracker when customer changes
  useEffect(() => {
    if (form.customer_id) {
      getOrders({ customer_id: form.customer_id, page_size: 1000 }).then((r) => setOrders(r.items))
      getContracts({ customer_id: form.customer_id, page_size: 1000 }).then((r) => setContracts(r.items))
      getCustomer(form.customer_id).then((c) => {
        setSelectedCustomerHasTracker(Boolean(c.token_tracker_url))
        setSelectedCustomerTrackerUrl(c.token_tracker_url || '')
      }).catch(() => { setSelectedCustomerHasTracker(false); setSelectedCustomerTrackerUrl('') })
    } else {
      setOrders([])
      setContracts([])
      setSelectedCustomerHasTracker(false)
      setSelectedCustomerTrackerUrl('')
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

  const handleAiImport = async () => {
    if (!selectedCustomerTrackerUrl) return
    setAiImportLoading(true)
    try {
      // Parse URLs from tracker field (supports single URL or JSON array with objects)
      let urls: string[]
      try {
        const parsed = JSON.parse(selectedCustomerTrackerUrl)
        if (!Array.isArray(parsed)) urls = [selectedCustomerTrackerUrl]
        else urls = parsed.map((item: string | { url: string }) => typeof item === 'string' ? item : item.url)
      } catch {
        urls = [selectedCustomerTrackerUrl]
      }

      const params = new URLSearchParams()
      if (aiImportFrom) params.set('from', aiImportFrom)
      if (aiImportTo) params.set('to', aiImportTo)
      const paramStr = params.toString()

      // Fetch all URLs and merge
      const results = await Promise.all(
        urls.map(u => {
          const sep = u.includes('?') ? '&' : '?'
          const url = paramStr ? `${u}${sep}${paramStr}` : u
          return axios.get<TokenTrackerData>(url).then(r => r.data)
        })
      )

      const totalActiveMin = results.reduce((s, r) => s + (r.summary.total_active_min || 0), 0)
      const totalCost = results.reduce((s, r) => s + (r.summary.total_cost || 0), 0)
      const totalSessions = results.reduce((s, r) => s + (r.summary.total_sessions || 0), 0)
      const totalLinesWritten = results.reduce((s, r) => s + (r.summary.lines_written || 0), 0)

      if (totalActiveMin === 0) {
        toast.error('Keine KI-Arbeitszeit im gewählten Zeitraum.')
        setAiImportLoading(false)
        return
      }

      const hours = Math.round(totalActiveMin / 60 * 100) / 100 // round to 2 decimals
      const periodFrom = aiImportFrom || 'Beginn'
      const periodTo = aiImportTo || 'heute'

      const newPositions: InvoicePosition[] = []
      const nextPos = form.positions.filter(p => p.beschreibung).length + 1

      // Position 1: AI-assisted development hours
      newPositions.push({
        position: nextPos,
        beschreibung: `KI-gestützte Entwicklung (${periodFrom} – ${periodTo})`,
        menge: hours,
        einheit: 'Stunden',
        einzelpreis: aiHourlyRate,
        gesamt: Math.round(hours * aiHourlyRate * 100) / 100,
      })

      // Position 2: AI API costs (if > 0)
      if (totalCost > 0) {
        const costEur = Math.round(totalCost * 0.92 * 100) / 100
        newPositions.push({
          position: nextPos + 1,
          beschreibung: `KI-API-Kosten (${totalSessions} Sessions, ${totalLinesWritten.toLocaleString('de-DE')} Codezeilen)`,
          menge: 1,
          einheit: 'pauschal',
          einzelpreis: costEur,
          gesamt: costEur,
        })
      }

      // Add to existing positions (replace empty first position if exists)
      let existingPositions = form.positions.filter(p => p.beschreibung.trim() !== '')
      const allPositions = [...existingPositions, ...newPositions].map((p, i) => ({
        ...p,
        position: i + 1,
        gesamt: p.menge * p.einzelpreis,
      }))

      setForm({
        ...form,
        positions: allPositions.length > 0 ? allPositions : [{ ...emptyPosition }],
        token_usage_from: aiImportFrom || null,
        token_usage_to: aiImportTo || null,
      })

      setShowAiImport(false)
      toast.success(`${hours} Stunden KI-Arbeitszeit importiert.`)
    } catch {
      toast.error('Fehler beim Laden der KI-Daten.')
    }
    setAiImportLoading(false)
  }

  const positionsNetto = form.positions.reduce((sum, p) => sum + p.menge * p.einzelpreis, 0)
  const discountAmount = discountEnabled && discountValue
    ? (discountPercent ? positionsNetto * (parseFloat(discountValue) || 0) / 100 : parseFloat(discountValue) || 0)
    : 0
  const netto = positionsNetto - discountAmount
  const taxRate = form.tax_rate || 0
  const taxAmount = netto * (taxRate / 100)
  const brutto = netto + taxAmount

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    const allPositions = form.positions.map((p, i) => ({
      ...p,
      position: i + 1,
      gesamt: p.menge * p.einzelpreis,
    }))

    // Add discount as negative position
    if (discountEnabled && discountAmount > 0) {
      const reason = discountReason || 'Rabatt'
      allPositions.push({
        position: allPositions.length + 1,
        beschreibung: `Rabatt: ${reason}${discountPercent ? ` (${discountValue}%)` : ''}`,
        menge: 1,
        einheit: 'pauschal',
        einzelpreis: -discountAmount,
        gesamt: -discountAmount,
      })
    }

    const payload: InvoiceCreate = {
      ...form,
      positions: allPositions,
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Rechnung bearbeiten' : 'Neue Rechnung'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
          <h3 className="text-sm font-semibold text-text uppercase tracking-wider">Allgemein</h3>

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

          <AutocompleteInput label="Titel" name="title" value={form.title} onChange={handleChange} required placeholder="z.B. Website-Erstellung, SEO-Optimierung..." />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="Rechnungsdatum"
              name="invoice_date"
              type="date"
              value={form.invoice_date || ''}
              onChange={handleChange}
            />
            <FormField
              label="Fälligkeitsdatum"
              name="due_date"
              type="date"
              value={form.due_date || ''}
              onChange={handleChange}
            />
          </div>
        </div>

        {/* Positions */}
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-text uppercase tracking-wider">Positionen</h3>
            <div className="flex gap-2">
              {selectedCustomerHasTracker && (
                <button type="button" onClick={() => setShowAiImport(!showAiImport)} className="btn-primary !text-xs !py-1.5 !px-3">
                  KI-Arbeitszeit importieren
                </button>
              )}
              <button type="button" onClick={addPosition} className="btn-secondary text-sm">
                Position hinzufügen
              </button>
            </div>
          </div>

          {/* AI Import Panel */}
          {showAiImport && (
            <div className="bg-surface-2 border border-accent/30 rounded-lg p-4 mb-4">
              <h4 className="text-sm font-medium text-accent mb-3">KI-Arbeitszeit aus Token Tracker importieren</h4>
              <p className="text-xs text-text-muted mb-3">Importiert die aktive KI-Arbeitszeit und API-Kosten als Rechnungspositionen.</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-1">Von</label>
                  <input type="date" value={aiImportFrom} onChange={e => setAiImportFrom(e.target.value)} className="w-full !py-1.5 !text-sm" />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-1">Bis</label>
                  <input type="date" value={aiImportTo} onChange={e => setAiImportTo(e.target.value)} className="w-full !py-1.5 !text-sm" />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-1">Stundensatz (€)</label>
                  <input type="number" value={aiHourlyRate} onChange={e => setAiHourlyRate(parseFloat(e.target.value) || 0)} min="0" step="5" className="w-full !py-1.5 !text-sm" />
                </div>
                <div className="flex items-end">
                  <button type="button" onClick={handleAiImport} disabled={aiImportLoading} className="btn-primary w-full !py-1.5 !text-sm">
                    {aiImportLoading ? 'Laden...' : 'Importieren'}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-text-muted">Erstellt zwei Positionen: Arbeitszeit (Stunden × Satz) + KI-API-Kosten (pauschal). Der KI-Nutzungsbericht kann optional als PDF-Anhang beigefügt werden.</p>
            </div>
          )}

          <div className="space-y-3">
            {/* Header */}
            <div className="hidden md:grid md:grid-cols-12 gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider px-1">
              <div className="col-span-4">Beschreibung</div>
              <div className="col-span-2">Menge</div>
              <div className="col-span-2">Einheit</div>
              <div className="col-span-2">Einzelpreis</div>
              <div className="col-span-1">Gesamt</div>
              <div className="col-span-1"></div>
            </div>

            {form.positions.map((pos, idx) => (
              <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 items-start bg-surface-2 rounded-lg p-2 md:p-0 md:bg-transparent">
                <div className="md:col-span-4">
                  <label className="md:hidden text-xs text-text-muted mb-1 block">Beschreibung</label>
                  <AutocompleteInput
                    name={`pos-${idx}-beschreibung`}
                    value={pos.beschreibung}
                    onChange={(e) => updatePosition(idx, 'beschreibung', e.target.value)}
                    placeholder="z.B. Technische Umsetzung, SEO..."
                    suggestions={POSITION_SUGGESTIONS}
                    compact
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="md:hidden text-xs text-text-muted mb-1 block">Menge</label>
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
                  <label className="md:hidden text-xs text-text-muted mb-1 block">Einheit</label>
                  <input
                    type="text"
                    value={pos.einheit}
                    onChange={(e) => updatePosition(idx, 'einheit', e.target.value)}
                    placeholder="Stunden"
                    className="input-field text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="md:hidden text-xs text-text-muted mb-1 block">Einzelpreis</label>
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
                  <label className="md:hidden text-xs text-text-muted mb-1 block mr-2">Gesamt</label>
                  <span className="text-sm text-text py-2">
                    {formatCurrency(pos.menge * pos.einzelpreis)}
                  </span>
                </div>
                <div className="md:col-span-1 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => removePosition(idx)}
                    disabled={form.positions.length <= 1}
                    className="p-1.5 text-text-muted hover:text-danger disabled:opacity-30 transition-colors"
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
          <div className="mt-6 pt-4 border-t border-border">
            <div className="flex items-center gap-3 mb-4">
              <label className="text-xs uppercase tracking-wider text-text-muted">USt.-Satz (%):</label>
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

            {/* Discount */}
            <div className="flex items-center gap-3 mb-4">
              <input
                type="checkbox"
                id="discount-toggle"
                checked={discountEnabled}
                onChange={(e) => setDiscountEnabled(e.target.checked)}
                className="w-4 h-4 accent-[#58a6ff]"
              />
              <label htmlFor="discount-toggle" className="text-xs uppercase tracking-wider text-text-muted cursor-pointer">Rabatt gewähren</label>
            </div>
            {discountEnabled && (
              <div className="flex flex-wrap items-end gap-3 mb-4 p-3 bg-surface-2 rounded-lg">
                <div>
                  <label className="block text-xs text-text-muted mb-1">Typ</label>
                  <select value={discountPercent ? 'percent' : 'fixed'} onChange={(e) => setDiscountPercent(e.target.value === 'percent')} className="w-auto !py-1.5 !text-sm">
                    <option value="percent">Prozent (%)</option>
                    <option value="fixed">Festbetrag (€)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">{discountPercent ? 'Rabatt (%)' : 'Rabatt (€)'}</label>
                  <input type="number" value={discountValue} onChange={(e) => setDiscountValue(e.target.value)} min="0" step={discountPercent ? '5' : '0.01'} max={discountPercent ? '100' : undefined} placeholder={discountPercent ? 'z.B. 10' : 'z.B. 50'} className="w-28 !py-1.5 !text-sm" />
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-xs text-text-muted mb-1">Begründung</label>
                  <AutocompleteInput
                    name="discount_reason"
                    value={discountReason}
                    onChange={(e) => setDiscountReason(e.target.value)}
                    placeholder="z.B. Treuerabatt, Erstkundenrabatt..."
                    suggestions={[
                      'Treuerabatt',
                      'Erstkundenrabatt',
                      'Mengenrabatt',
                      'Projektrabatt',
                      'Sonderkonditionen',
                      'Langfristige Zusammenarbeit',
                      'Empfehlungsrabatt',
                      'Non-Profit / Verein',
                      'Vorkasse-Rabatt',
                      'Paketpreis',
                      'Frühbucherrabatt',
                      'Nachlass wegen Verzögerung',
                      'Kulanz',
                      'Bestandskundenrabatt',
                      'Jubiläumsrabatt',
                    ]}
                    compact
                  />
                </div>
                {discountAmount > 0 && (
                  <div className="text-sm text-success font-medium tabular-nums whitespace-nowrap">
                    −{formatCurrency(discountAmount)}
                  </div>
                )}
              </div>
            )}

            <div className="flex flex-col items-end gap-1">
              <div className="flex justify-between w-72">
                <span className="text-sm text-text-muted">Zwischensumme:</span>
                <span className="text-sm text-text font-medium tabular-nums">{formatCurrency(positionsNetto)}</span>
              </div>
              {discountAmount > 0 && (
                <div className="flex justify-between w-72">
                  <span className="text-sm text-success">Rabatt:</span>
                  <span className="text-sm text-success font-medium tabular-nums">−{formatCurrency(discountAmount)}</span>
                </div>
              )}
              <div className="flex justify-between w-72">
                <span className="text-sm text-text-muted">Netto:</span>
                <span className="text-sm text-text font-medium tabular-nums">{formatCurrency(netto)}</span>
              </div>
              <div className="flex justify-between w-72">
                <span className="text-sm text-text-muted">USt. ({taxRate}%):</span>
                <span className="text-sm text-text font-medium tabular-nums">{formatCurrency(taxAmount)}</span>
              </div>
              <div className="flex justify-between w-72 pt-2 border-t border-border">
                <span className="text-sm font-semibold text-text">Brutto:</span>
                <span className="text-sm font-bold text-accent tabular-nums">{formatCurrency(brutto)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <FormField
            label="Notizen"
            name="notes"
            type="textarea"
            value={form.notes || ''}
            onChange={handleChange}
            placeholder="Optionale Anmerkungen zur Rechnung..."
          />
        </div>

        {/* KI-Nutzungsbericht */}
        {selectedCustomerHasTracker && (
          <div className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="attach-token-usage"
                checked={attachTokenUsage}
                onChange={(e) => {
                  setAttachTokenUsage(e.target.checked)
                  if (e.target.checked) {
                    const now = new Date()
                    const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
                    const today = now.toISOString().split('T')[0]
                    setForm({ ...form, token_usage_from: firstOfMonth, token_usage_to: today })
                  } else {
                    setForm({ ...form, token_usage_from: null, token_usage_to: null })
                  }
                }}
                className="w-4 h-4 accent-[#58a6ff]"
              />
              <label htmlFor="attach-token-usage" className="text-sm font-semibold text-text cursor-pointer">
                KI-Nutzungsbericht an Rechnung anhängen
              </label>
            </div>
            {attachTokenUsage && (
              <div>
                <p className="text-xs text-text-muted mb-3">
                  Der Bericht zeigt dem Kunden transparent, welche KI-gestützte Entwicklungsarbeit im gewählten Zeitraum stattfand.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Zeitraum von</label>
                    <input
                      type="date"
                      value={form.token_usage_from || ''}
                      onChange={(e) => setForm({ ...form, token_usage_from: e.target.value || null })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Zeitraum bis</label>
                    <input
                      type="date"
                      value={form.token_usage_to || ''}
                      onChange={(e) => setForm({ ...form, token_usage_to: e.target.value || null })}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

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
