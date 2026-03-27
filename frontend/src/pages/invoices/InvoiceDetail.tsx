import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  getInvoice,
  deleteInvoice,
  generatePdf,
  downloadPdf,
  updateInvoiceStatus,
} from '../../api/invoices'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Invoice } from '../../types'

export default function InvoiceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [showDelete, setShowDelete] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    getInvoice(id).then(setInvoice)
  }, [id])

  const handleDelete = async () => {
    try {
      await deleteInvoice(id!)
      toast.success('Rechnung geloescht.')
      navigate('/rechnungen')
    } catch {
      toast.error('Fehler beim Loeschen.')
    }
  }

  const handleGeneratePdf = async () => {
    setPdfLoading(true)
    try {
      await generatePdf(id!)
      toast.success('PDF wurde generiert.')
      // Reload invoice to get pdf_path
      const updated = await getInvoice(id!)
      setInvoice(updated)
    } catch {
      toast.error('Fehler beim Generieren der PDF.')
    }
    setPdfLoading(false)
  }

  const handleDownloadPdf = async () => {
    try {
      const blob = await downloadPdf(id!)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${invoice?.invoice_number || 'rechnung'}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Fehler beim Herunterladen der PDF.')
    }
  }

  const handleStatusChange = async (newStatus: 'gestellt' | 'bezahlt') => {
    try {
      const updated = await updateInvoiceStatus(id!, newStatus)
      setInvoice(updated)
      toast.success(
        newStatus === 'gestellt'
          ? 'Rechnung als gestellt markiert.'
          : 'Rechnung als bezahlt markiert.',
      )
    } catch {
      toast.error('Fehler beim Aktualisieren des Status.')
    }
  }

  if (!invoice) {
    return <div className="text-gray-500 py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/rechnungen')} className="text-gray-400 hover:text-gray-200">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-100">{invoice.invoice_number}</h2>
            <p className="text-sm text-gray-400">{invoice.title}</p>
          </div>
          <StatusBadge status={invoice.status} />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={handleGeneratePdf}
            disabled={pdfLoading}
            className="btn-secondary text-sm"
          >
            {pdfLoading ? 'Generiert...' : 'PDF generieren'}
          </button>
          {invoice.pdf_path && (
            <button onClick={handleDownloadPdf} className="btn-secondary text-sm">
              PDF herunterladen
            </button>
          )}
          {invoice.status === 'entwurf' && (
            <button
              onClick={() => handleStatusChange('gestellt')}
              className="btn-primary text-sm"
            >
              Als gestellt markieren
            </button>
          )}
          {(invoice.status === 'gestellt' || invoice.status === 'ueberfaellig') && (
            <button
              onClick={() => handleStatusChange('bezahlt')}
              className="bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors"
            >
              Als bezahlt markieren
            </button>
          )}
          {invoice.status === 'entwurf' && (
            <>
              <button
                onClick={() => navigate(`/rechnungen/${id}/bearbeiten`)}
                className="btn-secondary text-sm"
              >
                Bearbeiten
              </button>
              <button onClick={() => setShowDelete(true)} className="btn-danger text-sm">
                Loeschen
              </button>
            </>
          )}
        </div>
      </div>

      {/* Invoice Info */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {invoice.customer_name && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Kunde</p>
              <p className="text-gray-200">{invoice.customer_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Rechnungsdatum</p>
            <p className="text-gray-200">{formatDate(invoice.invoice_date)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Faelligkeitsdatum</p>
            <p className="text-gray-200">{formatDate(invoice.due_date)}</p>
          </div>
        </div>
      </div>

      {/* Positions Table */}
      <div className="card mb-6">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Positionen</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-400 uppercase">Beschreibung</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase">Menge</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-400 uppercase">Einheit</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase">Einzelpreis</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-400 uppercase">Gesamt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {invoice.positions.map((pos, idx) => (
                <tr key={idx}>
                  <td className="px-4 py-3 text-sm text-gray-300">{pos.beschreibung}</td>
                  <td className="px-4 py-3 text-sm text-gray-300 text-right">{pos.menge}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{pos.einheit}</td>
                  <td className="px-4 py-3 text-sm text-gray-300 text-right">{formatCurrency(pos.einzelpreis)}</td>
                  <td className="px-4 py-3 text-sm text-gray-300 text-right">{formatCurrency(pos.gesamt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div className="mt-4 pt-4 border-t border-gray-700 flex flex-col items-end gap-1">
          <div className="flex justify-between w-64">
            <span className="text-sm text-gray-400">Netto:</span>
            <span className="text-sm text-gray-200">{formatCurrency(invoice.subtotal)}</span>
          </div>
          <div className="flex justify-between w-64">
            <span className="text-sm text-gray-400">USt. ({invoice.tax_rate}%):</span>
            <span className="text-sm text-gray-200">{formatCurrency(invoice.tax_amount)}</span>
          </div>
          <div className="flex justify-between w-64 pt-2 border-t border-gray-700">
            <span className="font-semibold text-gray-200">Brutto:</span>
            <span className="font-bold text-celox-400 text-lg">{formatCurrency(invoice.total)}</span>
          </div>
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="card mb-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Notizen</p>
          <p className="text-gray-300 text-sm whitespace-pre-wrap">{invoice.notes}</p>
        </div>
      )}

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Rechnung loeschen"
        message={`Moechten Sie die Rechnung "${invoice.invoice_number}" wirklich loeschen? Dies ist nur fuer Entwuerfe moeglich.`}
      />
    </div>
  )
}
