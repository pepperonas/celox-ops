import toast from 'react-hot-toast'

/**
 * Globales Undo-Muster: Erfolgs-Toast mit „Rückgängig"-Button.
 * `onUndo` führt die Umkehr-Aktion aus (z. B. alten Status wiederherstellen
 * oder ein gelöschtes Objekt neu anlegen). Fehler beim Undo werden als
 * Fehler-Toast gemeldet — die Aktion selbst ist dann bereits passiert.
 */
export function toastWithUndo(
  message: string,
  onUndo: () => void | Promise<void>,
  duration = 8000,
): void {
  toast(
    (t) => (
      <div className="flex items-center gap-3">
        <span className="text-sm">{message}</span>
        <button
          onClick={async () => {
            toast.dismiss(t.id)
            try {
              await onUndo()
              toast.success('Rückgängig gemacht.')
            } catch {
              toast.error('Rückgängig machen fehlgeschlagen.')
            }
          }}
          className="shrink-0 text-sm font-semibold text-accent hover:underline underline-offset-2 px-1"
        >
          Rückgängig
        </button>
      </div>
    ),
    { duration, icon: '✓' },
  )
}
