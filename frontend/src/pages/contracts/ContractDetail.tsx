import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getContract, deleteContract } from '../../api/contracts'
import { getInvoices } from '../../api/invoices'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Contract, Invoice } from '../../types'

export default function ContractDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [contract, setContract] = useState<Contract | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [showDelete, setShowDelete] = useState(false)

  useEffect(() => {
    if (!id) return
    getContract(id).then(setContract)
    getInvoices({ customer_id: id }).then((r) => setInvoices(r.items)).catch(() => {})
  }, [id])

  const handleDelete = async () => {
    try {
      await deleteContract(id!)
      toast.success('Vertrag gelöscht.')
      navigate('/vertraege')
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  if (!contract) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/vertraege')} className="text-text-muted hover:text-text">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold text-text">{contract.title}</h2>
          <StatusBadge status={contract.status} />
          <StatusBadge status={contract.type} />
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate(`/vertraege/${id}/bearbeiten`)} className="btn-secondary">
            Bearbeiten
          </button>
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Löschen
          </button>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contract.customer_name && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Kunde</p>
              <p className="text-text">{contract.customer_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Monatlicher Betrag</p>
            <p className="text-text">{formatCurrency(contract.monthly_amount)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Startdatum</p>
            <p className="text-text">{formatDate(contract.start_date)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Enddatum</p>
            <p className="text-text">{formatDate(contract.end_date)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Auto-Verlängerung</p>
            <p className="text-text">{contract.auto_renew ? 'Ja' : 'Nein'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Kündigungsfrist</p>
            <p className="text-text">{contract.notice_period_days} Tage</p>
          </div>
        </div>
        {contract.description && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs uppercase tracking-wider text-text-muted mb-1">Beschreibung</p>
            <p className="text-text text-sm whitespace-pre-wrap">{contract.description}</p>
          </div>
        )}
      </div>

      <h3 className="text-lg font-semibold text-text mb-3">Zugehörige Rechnungen</h3>
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
