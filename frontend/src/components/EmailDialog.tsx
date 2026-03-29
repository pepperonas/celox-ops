import { useEffect, useState } from 'react'
import { getEmailTemplates } from '../api/emailTemplates'
import type { EmailTemplate } from '../types'

interface EmailDialogProps {
  isOpen: boolean
  onClose: () => void
  defaultTo: string
  defaultSubject: string
  defaultMessage: string
  onSend: (data: { to_email: string; subject: string; message: string }) => Promise<void>
  placeholders?: Record<string, string>
}

export default function EmailDialog({
  isOpen,
  onClose,
  defaultTo,
  defaultSubject,
  defaultMessage,
  onSend,
  placeholders,
}: EmailDialogProps) {
  const [to, setTo] = useState(defaultTo)
  const [subject, setSubject] = useState(defaultSubject)
  const [message, setMessage] = useState(defaultMessage)
  const [sending, setSending] = useState(false)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('')

  // Reset fields when dialog opens with new defaults
  const [prevOpen, setPrevOpen] = useState(false)
  if (isOpen && !prevOpen) {
    setTo(defaultTo)
    setSubject(defaultSubject)
    setMessage(defaultMessage)
    setSelectedTemplate('')
  }
  if (isOpen !== prevOpen) setPrevOpen(isOpen)

  useEffect(() => {
    if (isOpen) {
      getEmailTemplates().then(setTemplates).catch(() => {})
    }
  }, [isOpen])

  const applyPlaceholders = (text: string): string => {
    if (!placeholders) return text
    let result = text
    for (const [key, value] of Object.entries(placeholders)) {
      result = result.split(`{${key}}`).join(value)
    }
    return result
  }

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId)
    if (!templateId) return
    const template = templates.find((t) => t.id === templateId)
    if (template) {
      setSubject(applyPlaceholders(template.subject))
      setMessage(applyPlaceholders(template.body))
    }
  }

  if (!isOpen) return null

  const handleSend = async () => {
    setSending(true)
    try {
      await onSend({ to_email: to, subject, message })
      onClose()
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-[16px] p-8 max-w-[520px] w-full mx-4">
        <h3 className="text-lg font-semibold text-text mb-5">E-Mail senden</h3>

        <div className="space-y-4">
          {templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">Vorlage</label>
              <select
                value={selectedTemplate}
                onChange={(e) => handleTemplateSelect(e.target.value)}
                className="input w-full"
              >
                <option value="">Keine Vorlage</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.category})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">An</label>
            <input
              type="email"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="input w-full"
              placeholder="email@beispiel.de"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Betreff</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="input w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Nachricht</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={8}
              className="input w-full resize-y"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="btn-secondary" disabled={sending}>
            Abbrechen
          </button>
          <button
            onClick={handleSend}
            className="btn-primary"
            disabled={sending || !to}
          >
            {sending ? 'Wird gesendet...' : 'Senden'}
          </button>
        </div>
      </div>
    </div>
  )
}
