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
      toast.success('Rechnung gelöscht.')
      navigate('/rechnungen')
    } catch {
      toast.error('Fehler beim Löschen.')
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
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/rechnungen')} className="text-text-muted hover:text-text">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h2 className="text-lg font-semibold text-text">{invoice.invoice_number}</h2>
            <p className="text-sm text-text-muted">{invoice.title}</p>
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
              className="bg-success hover:bg-success/90 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors"
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
                Löschen
</button>
            </>
          )}
        </div>
      </div>

      {/* Invoice Info */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {invoice.customer_name && (
            <div>
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Kunde</p>
              <p className="text-text">{invoice.customer_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Rechnungsdatum</p>
            <p className="text-text">{formatDate(invoice.invoice_date)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Fälligkeitsdatum</p>
            <p className="text-text">{formatDate(invoice.due_date)}</p>
          </div>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <h3 className="text-sm font-semibold text-text uppercase tracking-wider mb-4">Positionen</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Beschreibung</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">Menge</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Einheit</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">Einzelpreis</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">Gesamt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {invoice.positions.map((pos, idx) => (
                <tr key={idx}>
                  <td className="px-4 py-3 text-sm text-text">{pos.beschreibung}</td>
                  <td className="px-4 py-3 text-sm text-text text-right tabular-nums">{pos.menge}</td>
                  <td className="px-4 py-3 text-sm text-text-muted">{pos.einheit}</td>
                  <td className="px-4 py-3 text-sm text-text text-right tabular-nums">{formatCurrency(pos.einzelpreis)}</td>
                  <td className="px-4 py-3 text-sm text-text text-right tabular-nums">{formatCurrency(pos.gesamt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div className="mt-4 pt-4 border-t border-border flex flex-col items-end gap-1">
          <div className="flex justify-between w-64">
            <span className="text-sm text-text-muted">Netto:</span>
            <span className="text-sm text-text tabular-nums">{formatCurrency(invoice.subtotal)}</span>
          </div>
          <div className="flex justify-between w-64">
            <span className="text-sm text-text-muted">USt. ({invoice.tax_rate}%):</span>
            <span className="text-sm text-text tabular-nums">{formatCurrency(invoice.tax_amount)}</span>
          </div>
          <div className="flex justify-between w-64 pt-2 border-t border-border">
            <span className="font-semibold text-text">Brutto:</span>
            <span className="font-bold text-accent text-lg tabular-nums">{formatCurrency(invoice.total)}</span>
          </div>
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
          <p className="text-xs uppercase tracking-wider text-text-muted mb-1">Notizen</p>
          <p className="text-text text-sm whitespace-pre-wrap">{invoice.notes}</p>
        </div>
      )}

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Rechnung löschen"
        message={`Möchten Sie die Rechnung "${invoice.invoice_number}" wirklich löschen? Dies ist nur für Entwürfe möglich.`}
      />
    </div>
  )
}
