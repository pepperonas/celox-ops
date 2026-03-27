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
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-[16px] p-12 max-w-[400px] w-full mx-4">
        <h3 className="text-lg font-semibold text-text mb-2">{title}</h3>
        <p className="text-text-muted text-sm mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">
            Abbrechen
          </button>
          <button onClick={onConfirm} className="btn-danger">
            Löschen
          </button>
        </div>
      </div>
    </div>
  )
}
