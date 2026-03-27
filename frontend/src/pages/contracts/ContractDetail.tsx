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
    getContract(Number(id)).then(setContract)
    getInvoices({ customer_id: Number(id) }).then((r) => setInvoices(r.items)).catch(() => {})
  }, [id])

  const handleDelete = async () => {
    try {
      await deleteContract(Number(id))
      toast.success('Vertrag geloescht.')
      navigate('/vertraege')
    } catch {
      toast.error('Fehler beim Loeschen.')
    }
  }

  if (!contract) {
    return <div className="text-gray-500 py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/vertraege')} className="text-gray-400 hover:text-gray-200">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-2xl font-bold text-gray-100">{contract.titel}</h2>
          <StatusBadge status={contract.status} />
          <StatusBadge status={contract.typ} />
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate(`/vertraege/${id}/bearbeiten`)} className="btn-secondary">
            Bearbeiten
          </button>
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Loeschen
          </button>
        </div>
      </div>

      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contract.customer_name && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Kunde</p>
              <p className="text-gray-200">{contract.customer_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Monatlicher Betrag</p>
            <p className="text-gray-200">{formatCurrency(contract.monatlicher_betrag)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Startdatum</p>
            <p className="text-gray-200">{formatDate(contract.start_datum)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Enddatum</p>
            <p className="text-gray-200">{formatDate(contract.end_datum)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Auto-Verlaengerung</p>
            <p className="text-gray-200">{contract.auto_verlaengerung ? 'Ja' : 'Nein'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Kuendigungsfrist</p>
            <p className="text-gray-200">{contract.kuendigungsfrist_tage} Tage</p>
          </div>
        </div>
        {contract.beschreibung && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Beschreibung</p>
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{contract.beschreibung}</p>
          </div>
        )}
        {contract.notizen && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Notizen</p>
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{contract.notizen}</p>
          </div>
        )}
      </div>

      <h3 className="text-lg font-semibold text-gray-200 mb-3">Zugehoerige Rechnungen</h3>
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

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Vertrag loeschen"
        message={`Moechten Sie den Vertrag "${contract.titel}" wirklich loeschen?`}
      />
    </div>
  )
}
