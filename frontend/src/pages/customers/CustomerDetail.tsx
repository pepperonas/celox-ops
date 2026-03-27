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
    const numId = Number(id)
    getCustomer(numId).then(setCustomer)
    getOrders({ customer_id: numId }).then((r) => setOrders(r.items))
    getContracts({ customer_id: numId }).then((r) => setContracts(r.items))
    getInvoices({ customer_id: numId }).then((r) => setInvoices(r.items))
  }, [id])

  const handleDelete = async () => {
    try {
      await deleteCustomer(Number(id))
      toast.success('Kunde geloescht.')
      navigate('/kunden')
    } catch {
      toast.error('Fehler beim Loeschen.')
    }
  }

  if (!customer) {
    return <div className="text-gray-500 py-12 text-center">Laden...</div>
  }

  const tabs = [
    { key: 'auftraege' as const, label: `Auftraege (${orders.length})` },
    { key: 'vertraege' as const, label: `Vertraege (${contracts.length})` },
    { key: 'rechnungen' as const, label: `Rechnungen (${invoices.length})` },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/kunden')} className="text-gray-400 hover:text-gray-200">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-2xl font-bold text-gray-100">{customer.name}</h2>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate(`/kunden/${id}/bearbeiten`)} className="btn-secondary">
            Bearbeiten
          </button>
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Loeschen
          </button>
        </div>
      </div>

      {/* Info Card */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {customer.firma && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Firma</p>
              <p className="text-gray-200">{customer.firma}</p>
            </div>
          )}
          {customer.email && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">E-Mail</p>
              <p className="text-gray-200">{customer.email}</p>
            </div>
          )}
          {customer.telefon && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Telefon</p>
              <p className="text-gray-200">{customer.telefon}</p>
            </div>
          )}
          {customer.adresse && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Adresse</p>
              <p className="text-gray-200">
                {customer.adresse}
                {customer.plz || customer.ort
                  ? `, ${customer.plz} ${customer.ort}`
                  : ''}
              </p>
            </div>
          )}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Erstellt am</p>
            <p className="text-gray-200">{formatDate(customer.created_at)}</p>
          </div>
        </div>
        {customer.notizen && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Notizen</p>
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{customer.notizen}</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-800">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-celox-500 text-celox-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'auftraege' && (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-900/80 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Betrag</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Datum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {orders.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">Keine Auftraege vorhanden.</td></tr>
              ) : (
                orders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => navigate(`/auftraege/${o.id}`)}
                    className="hover:bg-gray-800/60 cursor-pointer"
                  >
                    <td className="px-4 py-3 text-sm text-gray-300">{o.titel}</td>
                    <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                    <td className="px-4 py-3 text-sm text-gray-300">{formatCurrency(o.betrag)}</td>
                    <td className="px-4 py-3 text-sm text-gray-400">{formatDate(o.start_datum)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'vertraege' && (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-900/80 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Typ</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Monatl.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {contracts.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">Keine Vertraege vorhanden.</td></tr>
              ) : (
                contracts.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/vertraege/${c.id}`)}
                    className="hover:bg-gray-800/60 cursor-pointer"
                  >
                    <td className="px-4 py-3 text-sm text-gray-300">{c.titel}</td>
                    <td className="px-4 py-3"><StatusBadge status={c.typ} /></td>
                    <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                    <td className="px-4 py-3 text-sm text-gray-300">{formatCurrency(c.monatlicher_betrag)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'rechnungen' && (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-900/80 border-b border-gray-800">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Nr.</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase">Brutto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {invoices.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">Keine Rechnungen vorhanden.</td></tr>
              ) : (
                invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => navigate(`/rechnungen/${inv.id}`)}
                    className="hover:bg-gray-800/60 cursor-pointer"
                  >
                    <td className="px-4 py-3 text-sm text-gray-300">{inv.rechnungsnummer}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{inv.titel}</td>
                    <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                    <td className="px-4 py-3 text-sm text-gray-300">{formatCurrency(inv.brutto_betrag)}</td>
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
        title="Kunde loeschen"
        message={`Moechten Sie den Kunden "${customer.name}" wirklich loeschen? Dieser Vorgang kann nicht rueckgaengig gemacht werden.`}
      />
    </div>
  )
}
