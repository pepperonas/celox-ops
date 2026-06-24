import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  markCompliance,
  uploadSignedDocument,
  type ComplianceCustomer,
} from '../api/compliance'
import { generateDocument } from '../api/documents'
import { downloadAttachment } from '../api/attachments'

interface Props {
  data: ComplianceCustomer | null
  onChanged: () => void
}

/** Kompakter Compliance-Block (Pflichtdokumente) für die Kundendetailansicht. */
export default function CustomerComplianceCard({ data, onChanged }: Props) {
  const [busy, setBusy] = useState<string | null>(null)

  if (!data || data.total_required === 0) return null
  const customerId = data.customer_id

  const handleGenerate = async (templateId: string, name: string) => {
    setBusy(templateId)
    try {
      await generateDocument(templateId, customerId)
      toast.success(`${name} erstellt.`)
    } catch {
      toast.error('PDF-Erstellung fehlgeschlagen.')
    }
    setBusy(null)
  }

  const pickAndUpload = (templateId: string) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,application/pdf,image/*'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      setBusy(templateId)
      try {
        await uploadSignedDocument(file, customerId, templateId)
        toast.success('Unterschriebenes Dokument hochgeladen.')
        onChanged()
      } catch {
        toast.error('Upload fehlgeschlagen.')
      }
      setBusy(null)
    }
    input.click()
  }

  const handleMark = async (templateId: string, signed: boolean) => {
    setBusy(templateId)
    try {
      await markCompliance({ customer_id: customerId, template_id: templateId, signed })
      toast.success(signed ? 'Als unterschrieben markiert.' : 'Markierung entfernt.')
      onChanged()
    } catch {
      toast.error('Aktion fehlgeschlagen.')
    }
    setBusy(null)
  }

  return (
    <div className="bg-surface border border-border rounded-card p-5 mb-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-text">Rechtsdokumente (Pflicht)</h3>
        {data.complete ? (
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-success/10 text-success">
            ✓ vollständig
          </span>
        ) : (
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-danger/10 text-danger">
            {data.missing_count} von {data.total_required} offen
          </span>
        )}
      </div>
      <div className="space-y-2">
        {data.items.map((item) => (
          <div
            key={item.template_id}
            className="flex items-center justify-between gap-3 py-2 border-t border-border first:border-t-0 flex-wrap"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${item.signed ? 'bg-success' : 'bg-danger'}`} />
              <span className="text-sm text-text truncate">{item.name}</span>
              {item.signed && (
                <span className="text-[11px] text-text-muted shrink-0">
                  {item.method === 'upload' ? 'hochgeladen' : 'manuell'}
                  {item.signed_at ? ` · ${new Date(item.signed_at).toLocaleDateString('de-DE')}` : ''}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {item.signed ? (
                <>
                  {item.attachment_id && (
                    <button
                      onClick={() => downloadAttachment(item.attachment_id!, `${item.name}.pdf`)}
                      className="text-xs px-2 py-1 rounded-lg text-accent hover:bg-accent/10"
                    >
                      Anzeigen
                    </button>
                  )}
                  <button
                    onClick={() => handleMark(item.template_id, false)}
                    disabled={busy === item.template_id}
                    className="text-xs px-2 py-1 rounded-lg text-text-muted hover:bg-danger/10 hover:text-danger disabled:opacity-50"
                  >
                    Zurücksetzen
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => handleGenerate(item.template_id, item.name)}
                    disabled={busy === item.template_id}
                    className="text-xs px-2.5 py-1 rounded-lg bg-accent/10 text-accent hover:bg-accent/20 disabled:opacity-50"
                  >
                    {busy === item.template_id ? '…' : 'PDF erstellen'}
                  </button>
                  <button
                    onClick={() => pickAndUpload(item.template_id)}
                    disabled={busy === item.template_id}
                    className="text-xs px-2.5 py-1 rounded-lg bg-surface-2 text-text hover:bg-border disabled:opacity-50"
                  >
                    Hochladen
                  </button>
                  <button
                    onClick={() => handleMark(item.template_id, true)}
                    disabled={busy === item.template_id}
                    className="text-xs px-2.5 py-1 rounded-lg text-success hover:bg-success/10 disabled:opacity-50"
                  >
                    Abhaken
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
