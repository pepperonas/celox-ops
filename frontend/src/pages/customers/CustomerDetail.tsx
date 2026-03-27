import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getCustomer, deleteCustomer } from '../../api/customers'
import { getOrders } from '../../api/orders'
import { getContracts } from '../../api/contracts'
import { getInvoices, createQuickInvoice } from '../../api/invoices'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import TokenUsage from '../../components/TokenUsage'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Customer, Order, Contract, Invoice } from '../../types'

export default function CustomerDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])

  const validTabs = ['auftraege', 'vertraege', 'rechnungen', 'tokens'] as const
  type TabKey = typeof validTabs[number]
  const hashTab = location.hash.replace('#', '') as TabKey
  const initialTab = validTabs.includes(hashTab) ? hashTab : 'auftraege'
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab)

  const switchTab = useCallback((tab: TabKey) => {
    setActiveTab(tab)
    navigate(`#${tab}`, { replace: true })
  }, [navigate])
  const [showDelete, setShowDelete] = useState(false)
  const [showQuickInvoice, setShowQuickInvoice] = useState(false)
  const [quickForm, setQuickForm] = useState({ beschreibung: '', menge: '1', einheit: 'pauschal', einzelpreis: '', notes: '' })
  const [quickLoading, setQuickLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    getCustomer(id).then(setCustomer)
    getOrders({ customer_id: id }).then((r) => setOrders(r.items))
    getContracts({ customer_id: id }).then((r) => setContracts(r.items))
    getInvoices({ customer_id: id }).then((r) => setInvoices(r.items))
  }, [id])


  const handleDelete = async () => {
    try {
      await deleteCustomer(id!)
      toast.success('Kunde gelöscht.')
      navigate('/kunden')
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  const handleQuickInvoice = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    setQuickLoading(true)
    try {
      const inv = await createQuickInvoice({
        customer_id: id,
        beschreibung: quickForm.beschreibung,
        menge: parseFloat(quickForm.menge) || 1,
        einheit: quickForm.einheit,
        einzelpreis: parseFloat(quickForm.einzelpreis) || 0,
        notes: quickForm.notes || undefined,
      })
      toast.success(`Schnellrechnung ${inv.invoice_number} erstellt.`)
      setShowQuickInvoice(false)
      setQuickForm({ beschreibung: '', menge: '1', einheit: 'pauschal', einzelpreis: '', notes: '' })
      getInvoices({ customer_id: id }).then((r) => setInvoices(r.items))
      navigate(`/rechnungen/${inv.id}`)
    } catch {
      toast.error('Fehler beim Erstellen der Schnellrechnung.')
    }
    setQuickLoading(false)
  }

  if (!customer) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  const tabs = [
    { key: 'auftraege' as const, label: `Aufträge (${orders.length})` },
    { key: 'vertraege' as const, label: `Verträge (${contracts.length})` },
    { key: 'rechnungen' as const, label: `Rechnungen (${invoices.length})` },
    ...(customer.token_tracker_url ? [{ key: 'tokens' as const, label: 'KI-Nutzung' }] : []),
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/kunden')} className="text-text-muted hover:text-text">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold text-text">{customer.name}</h2>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowQuickInvoice(true)} className="btn-primary">
            Schnellrechnung
          </button>
          <button onClick={() => navigate(`/kunden/${id}/bearbeiten`)} className="btn-secondary">
            Bearbeiten
          </button>
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Löschen
          </button>
        </div>
      </div>

      {/* Info Card */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {customer.company && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Firma</p>
              <p className="text-text">{customer.company}</p>
            </div>
          )}
          {customer.email && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">E-Mail</p>
              <p className="text-text">{customer.email}</p>
            </div>
          )}
          {customer.phone && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Telefon</p>
              <p className="text-text">{customer.phone}</p>
            </div>
          )}
          {customer.website && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Website</p>
              <a href={customer.website.startsWith('http') ? customer.website : `https://${customer.website}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-hover transition-colors">{customer.website}</a>
            </div>
          )}
          {customer.address && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Adresse</p>
              <p className="text-text">{customer.address}</p>
            </div>
          )}
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Erstellt am</p>
            <p className="text-text">{formatDate(customer.created_at)}</p>
          </div>
        </div>
        {customer.notes && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs uppercase tracking-wider text-text-muted mb-1">Notizen</p>
            <p className="text-text text-sm whitespace-pre-wrap">{customer.notes}</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => switchTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'auftraege' && (
        <div className="overflow-x-auto bg-surface border border-border rounded-[12px]">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-2 border-b border-border">
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Betrag</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Datum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {orders.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-text-muted">Keine Aufträge vorhanden.</td></tr>
              ) : (
                orders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => navigate(`/auftraege/${o.id}`)}
                    className="hover:bg-surface-2 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-text">{o.title}</td>
                    <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                    <td className="px-4 py-3 text-sm text-text">{formatCurrency(o.amount)}</td>
                    <td className="px-4 py-3 text-sm text-text-muted">{formatDate(o.start_date)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'vertraege' && (
        <div className="overflow-x-auto bg-surface border border-border rounded-[12px]">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-2 border-b border-border">
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Typ</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Monatl.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {contracts.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-text-muted">Keine Verträge vorhanden.</td></tr>
              ) : (
                contracts.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/vertraege/${c.id}`)}
                    className="hover:bg-surface-2 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-text">{c.title}</td>
                    <td className="px-4 py-3"><StatusBadge status={c.type} /></td>
                    <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                    <td className="px-4 py-3 text-sm text-text">{formatCurrency(c.monthly_amount)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'rechnungen' && (
        <div className="overflow-x-auto bg-surface border border-border rounded-[12px]">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-2 border-b border-border">
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Nr.</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Brutto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {invoices.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-text-muted">Keine Rechnungen vorhanden.</td></tr>
              ) : (
                invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => navigate(`/rechnungen/${inv.id}`)}
                    className="hover:bg-surface-2 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-text">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-sm text-text">{inv.title}</td>
                    <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                    <td className="px-4 py-3 text-sm text-text">{formatCurrency(inv.total)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'tokens' && customer.token_tracker_url && (
        <TokenUsage trackerUrl={customer.token_tracker_url} />
      )}

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Kunde löschen"
        message={`Möchten Sie den Kunden "${customer.name}" wirklich löschen? Dieser Vorgang kann nicht rückgängig gemacht werden.`}
      />

      {/* Schnellrechnung Modal */}
      {showQuickInvoice && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50" onClick={() => setShowQuickInvoice(false)}>
          <div className="bg-surface border border-border rounded-[16px] p-8 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-text mb-1">Schnellrechnung</h3>
            <p className="text-text-muted text-sm mb-6">Für {customer.name} — ohne Auftrag/Vertrag</p>
            <form onSubmit={handleQuickInvoice} className="space-y-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Beschreibung *</label>
                <input
                  type="text"
                  value={quickForm.beschreibung}
                  onChange={(e) => setQuickForm({ ...quickForm, beschreibung: e.target.value })}
                  placeholder="z.B. Sicherheitscheck Website"
                  className="w-full"
                  required
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Menge</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0.25"
                    value={quickForm.menge}
                    onChange={(e) => setQuickForm({ ...quickForm, menge: e.target.value })}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Einheit</label>
                  <select
                    value={quickForm.einheit}
                    onChange={(e) => setQuickForm({ ...quickForm, einheit: e.target.value })}
                    className="w-full"
                  >
                    <option value="pauschal">pauschal</option>
                    <option value="Stunden">Stunden</option>
                    <option value="Stück">Stück</option>
                    <option value="Monat">Monat</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Einzelpreis (€) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={quickForm.einzelpreis}
                    onChange={(e) => setQuickForm({ ...quickForm, einzelpreis: e.target.value })}
                    placeholder="0,00"
                    className="w-full"
                    required
                  />
                </div>
              </div>
              {quickForm.einzelpreis && (
                <div className="text-right text-sm text-text-muted">
                  Gesamt: <span className="text-accent font-semibold">{formatCurrency((parseFloat(quickForm.menge) || 1) * (parseFloat(quickForm.einzelpreis) || 0))}</span>
                </div>
              )}
              <div>
                <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Notiz (optional)</label>
                <input
                  type="text"
                  value={quickForm.notes}
                  onChange={(e) => setQuickForm({ ...quickForm, notes: e.target.value })}
                  placeholder="z.B. Telefonisch beauftragt"
                  className="w-full"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowQuickInvoice(false)} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={quickLoading} className="btn-primary">
                  {quickLoading ? 'Erstellen...' : 'Rechnung erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
