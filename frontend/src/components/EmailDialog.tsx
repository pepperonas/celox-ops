import { useState } from 'react'

interface EmailDialogProps {
  isOpen: boolean
  onClose: () => void
  defaultTo: string
  defaultSubject: string
  defaultMessage: string
  onSend: (data: { to_email: string; subject: string; message: string }) => Promise<void>
}

export default function EmailDialog({
  isOpen,
  onClose,
  defaultTo,
  defaultSubject,
  defaultMessage,
  onSend,
}: EmailDialogProps) {
  const [to, setTo] = useState(defaultTo)
  const [subject, setSubject] = useState(defaultSubject)
  const [message, setMessage] = useState(defaultMessage)
  const [sending, setSending] = useState(false)

  // Reset fields when dialog opens with new defaults
  const [prevOpen, setPrevOpen] = useState(false)
  if (isOpen && !prevOpen) {
    setTo(defaultTo)
    setSubject(defaultSubject)
    setMessage(defaultMessage)
  }
  if (isOpen !== prevOpen) setPrevOpen(isOpen)

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
