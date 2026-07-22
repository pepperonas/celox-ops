import { useAuthStore } from '../../store/authStore'
import { canDelete } from '../../utils/permissions'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import { getContract, deleteContract } from '../../api/contracts'
import { getInvoices } from '../../api/invoices'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import FileAttachments from '../../components/FileAttachments'
import LoadingIndicator from '../../components/LoadingIndicator'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Contract, Invoice } from '../../types'

export default function ContractDetail() {
  const mayDelete = canDelete(useAuthStore((st) => st.role))
  const { id } = useParams()
  const navigate = useAppNavigate()
  const [contract, setContract] = useState<Contract | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [showDelete, setShowDelete] = useState(false)

  useEffect(() => {
    if (!id) return
    getContract(id).then(setContract)
    getInvoices({ customer_id: id }).then((r) => setInvoices(r.items)).catch((err) => console.warn("Daten konnten nicht geladen werden:", err))
  }, [id])

  const handleDelete = async () => {
    try {
      await deleteContract(id!)
      toast.success('Vertrag gelöscht.')
      navigate('/vertraege', { back: true })
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  if (!contract) {
    return <LoadingIndicator />
  }

  return (
    <div>
      <div className="flex flex-wrap justify-between items-center gap-3 mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/vertraege', { back: true })} className="md-state grid place-items-center w-10 h-10 rounded-full text-text-muted hover:text-text transition-colors duration-short">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-2xl font-semibold text-text tracking-tight">{contract.title}</h2>
          <StatusBadge status={contract.status} />
          <StatusBadge status={contract.type} />
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => navigate(`/vertraege/${id}/bearbeiten`)} className="btn-secondary">
            Bearbeiten
          </button>
          {mayDelete && (<button onClick={() => setShowDelete(true)} className="btn-danger">
            Löschen
          </button>)}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-card p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contract.customer_name && (
            <div>
              <p className="text-xs text-text-muted mb-2">Kunde</p>
              <p className="text-text">{contract.customer_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-text-muted mb-2">Monatlicher Betrag</p>
            <p className="text-text">{formatCurrency(contract.monthly_amount)}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-2">Zahlungsturnus</p>
            <p className="text-text">
              {{ monatlich: 'Monatlich', quartalsweise: 'Quartalsweise', halbjaehrlich: 'Halbjährlich', jaehrlich: 'Jährlich' }[contract.billing_cycle] || contract.billing_cycle || 'Monatlich'}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-2">Startdatum</p>
            <p className="text-text">{formatDate(contract.start_date)}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-2">Enddatum</p>
            <p className="text-text">{formatDate(contract.end_date)}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-2">Auto-Verlängerung</p>
            <p className="text-text">{contract.auto_renew ? 'Ja' : 'Nein'}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted mb-2">Kündigungsfrist</p>
            <p className="text-text">{contract.notice_period_days} Tage</p>
          </div>
        </div>
        {contract.description && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs text-text-muted mb-1">Beschreibung</p>
            <p className="text-text text-sm whitespace-pre-wrap">{contract.description}</p>
          </div>
        )}
      </div>

      {/* Anhänge */}
      <div className="mb-6">
        <FileAttachments contract_id={id} />
      </div>

      <h3 className="text-lg font-semibold text-text mb-3">Zugehörige Rechnungen</h3>
      <div className="overflow-x-auto bg-surface border border-border rounded-card">
        <table className="w-full">
          <thead>
            <tr className="bg-surface-2 border-b border-border">
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted">Nr.</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted">Titel</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted">Brutto</th>
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

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Vertrag löschen"
        message={`Möchten Sie den Vertrag "${contract.title}" wirklich löschen?`}
      />
    </div>
  )
}
