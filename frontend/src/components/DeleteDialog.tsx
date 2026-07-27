import { useEffect } from 'react'
import { createPortal } from 'react-dom'

interface DeleteDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
}

export default function DeleteDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
}: DeleteDialogProps) {
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'Enter') onConfirm()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose, onConfirm])

  if (!isOpen) return null

  // An document.body portalt (Repo-Regel): waehrend der Seiten-Reveal-Animation
  // ist `.page-enter` transformiert und wuerde als Containing-Block fuer
  // position:fixed dienen -> der Dialog saesse falsch.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-xl shadow-elev-3 p-8 max-w-[400px] w-full mx-4 animate-md-scale">
        <h3 className="text-xl font-semibold text-text mb-3">{title}</h3>
        <p className="text-text-muted text-sm mb-7 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">
            Abbrechen
          </button>
          <button onClick={onConfirm} className="btn-danger">
            Löschen
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
