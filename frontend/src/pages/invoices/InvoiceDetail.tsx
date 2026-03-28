import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  getInvoice,
  deleteInvoice,
  generatePdf,
  downloadPdf,
  updateInvoiceStatus,
  sendReminder,
  generateReminderPdf,
  downloadReminderPdf,
  sendInvoiceEmail,
  sendReminderEmail,
} from '../../api/invoices'
import { getCustomer } from '../../api/customers'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import EmailDialog from '../../components/EmailDialog'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Invoice } from '../../types'

export default function InvoiceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [showDelete, setShowDelete] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [reminderLoading, setReminderLoading] = useState(false)
  const [reminderPdfLoading, setReminderPdfLoading] = useState(false)
  const [showEmailDialog, setShowEmailDialog] = useState(false)
  const [showReminderEmailDialog, setShowReminderEmailDialog] = useState(false)
  const [customerEmail, setCustomerEmail] = useState('')

  useEffect(() => {
    if (!id) return
    getInvoice(id).then((inv) => {
      setInvoice(inv)
      if (inv.customer_id) {
        getCustomer(inv.customer_id).then((c) => setCustomerEmail(c.email || '')).catch(() => {})
      }
    })
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

  const handleViewPdf = async () => {
    try {
      const blob = await downloadPdf(id!)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch {
      toast.error('Fehler beim Öffnen der PDF.')
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

  const reminderLevelLabel = (level: number) => {
    switch (level) {
      case 1: return 'Zahlungserinnerung'
      case 2: return '1. Mahnung'
      case 3: return 'Letzte Mahnung'
      default: return 'Keine Mahnung'
    }
  }

  const isOverdue = invoice
    ? (invoice.status === 'gestellt' || invoice.status === 'ueberfaellig') &&
      new Date(invoice.due_date) < new Date()
    : false

  const canRemind = isOverdue && (invoice?.reminder_level ?? 0) < 3

  const handleSendReminder = async () => {
    setReminderLoading(true)
    try {
      const updated = await sendReminder(id!)
      setInvoice(updated)
      toast.success(`${reminderLevelLabel(updated.reminder_level)} wurde gesendet.`)
    } catch {
      toast.error('Fehler beim Senden der Mahnung.')
    }
    setReminderLoading(false)
  }

  const handleGenerateReminderPdf = async () => {
    setReminderPdfLoading(true)
    try {
      await generateReminderPdf(id!)
      toast.success('Mahnungs-PDF wurde generiert.')
      const updated = await getInvoice(id!)
      setInvoice(updated)
    } catch {
      toast.error('Fehler beim Generieren der Mahnungs-PDF.')
    }
    setReminderPdfLoading(false)
  }

  const handleDownloadReminderPdf = async () => {
    try {
      const blob = await downloadReminderPdf(id!)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Mahnung_${invoice?.invoice_number || 'mahnung'}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Fehler beim Herunterladen der Mahnungs-PDF.')
    }
  }

  const handleViewReminderPdf = async () => {
    try {
      const blob = await downloadReminderPdf(id!)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch {
      toast.error('Fehler beim Öffnen der Mahnungs-PDF.')
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
          {invoice.reminder_level > 0 && (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              invoice.reminder_level === 3
                ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                : invoice.reminder_level === 2
                  ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400'
                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
            }`}>
              {reminderLevelLabel(invoice.reminder_level)}
            </span>
          )}
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
            <>
              <button onClick={handleViewPdf} className="btn-primary text-sm">
                PDF anzeigen
              </button>
              <button onClick={handleDownloadPdf} className="btn-secondary text-sm">
                PDF herunterladen
              </button>
              <button onClick={() => setShowEmailDialog(true)} className="btn-secondary text-sm">
                Per E-Mail senden
              </button>
            </>
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
          {canRemind && (
            <button
              onClick={handleSendReminder}
              disabled={reminderLoading}
              className="bg-warning hover:bg-warning/90 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors"
            >
              {reminderLoading ? 'Wird gesendet...' : 'Mahnung senden'}
            </button>
          )}
          {invoice.reminder_level > 0 && (
            <button
              onClick={handleGenerateReminderPdf}
              disabled={reminderPdfLoading}
              className="btn-secondary text-sm"
            >
              {reminderPdfLoading ? 'Generiert...' : 'Mahnungs-PDF generieren'}
            </button>
          )}
          {invoice.reminder_pdf_path && (
            <>
              <button onClick={handleViewReminderPdf} className="btn-primary text-sm">
                Mahnungs-PDF anzeigen
              </button>
              <button onClick={handleDownloadReminderPdf} className="btn-secondary text-sm">
                Mahnungs-PDF herunterladen
              </button>
              <button onClick={() => setShowReminderEmailDialog(true)} className="btn-secondary text-sm">
                Mahnung per E-Mail senden
              </button>
            </>
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

      <EmailDialog
        isOpen={showEmailDialog}
        onClose={() => setShowEmailDialog(false)}
        defaultTo={customerEmail}
        defaultSubject={`Rechnung ${invoice.invoice_number}`}
        defaultMessage={`Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie die Rechnung ${invoice.invoice_number} über ${formatCurrency(invoice.total)}.\n\nBitte überweisen Sie den Betrag bis zum ${formatDate(invoice.due_date)}.\n\nBei Fragen stehen wir Ihnen gerne zur Verfügung.\n\nMit freundlichen Grüßen`}
        onSend={async (data) => {
          try {
            await sendInvoiceEmail(id!, data)
            toast.success('Rechnung wurde per E-Mail gesendet.')
          } catch (e: any) {
            const msg = e?.response?.data?.detail || 'Fehler beim E-Mail-Versand.'
            toast.error(msg)
            throw e
          }
        }}
      />

      <EmailDialog
        isOpen={showReminderEmailDialog}
        onClose={() => setShowReminderEmailDialog(false)}
        defaultTo={customerEmail}
        defaultSubject={`${reminderLevelLabel(invoice.reminder_level)} — Rechnung ${invoice.invoice_number}`}
        defaultMessage={`Sehr geehrte Damen und Herren,\n\nwir möchten Sie daran erinnern, dass die Rechnung ${invoice.invoice_number} über ${formatCurrency(invoice.total)} noch offen ist.\n\nDie Fälligkeit war am ${formatDate(invoice.due_date)}.\n\nBitte überweisen Sie den offenen Betrag umgehend.\n\nSollte sich Ihre Zahlung mit diesem Schreiben überschneiden, betrachten Sie diese Erinnerung bitte als gegenstandslos.\n\nMit freundlichen Grüßen`}
        onSend={async (data) => {
          try {
            await sendReminderEmail(id!, data)
            toast.success('Mahnung wurde per E-Mail gesendet.')
          } catch (e: any) {
            const msg = e?.response?.data?.detail || 'Fehler beim E-Mail-Versand.'
            toast.error(msg)
            throw e
          }
        }}
      />
    </div>
  )
}
