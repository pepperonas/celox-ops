import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getCustomer, deleteCustomer } from '../../api/customers'
import { getOrders } from '../../api/orders'
import { getContracts } from '../../api/contracts'
import { getInvoices } from '../../api/invoices'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Customer, Order, Contract, Invoice } from '../../types'

export default function CustomerDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [activeTab, setActiveTab] = useState<'auftraege' | 'vertraege' | 'rechnungen'>('auftraege')
  const [showDelete, setShowDelete] = useState(false)

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

  if (!customer) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  const tabs = [
    { key: 'auftraege' as const, label: `Aufträge (${orders.length})` },
    { key: 'vertraege' as const, label: `Verträge (${contracts.length})` },
    { key: 'rechnungen' as const, label: `Rechnungen (${invoices.length})` },
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
            onClick={() => setActiveTab(tab.key)}
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

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Kunde löschen"
        message={`Möchten Sie den Kunden "${customer.name}" wirklich löschen? Dieser Vorgang kann nicht rückgängig gemacht werden.`}
      />
    </div>
  )
}
