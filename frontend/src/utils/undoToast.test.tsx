import { describe, it, expect, vi, beforeEach } from 'vitest'

// react-hot-toast mocken — wir prüfen das Verhalten der Undo-Utility,
// nicht das Rendering der Toast-Bibliothek.
vi.mock('react-hot-toast', () => {
  const toastFn = vi.fn() as ReturnType<typeof vi.fn> & {
    dismiss: ReturnType<typeof vi.fn>
    success: ReturnType<typeof vi.fn>
    error: ReturnType<typeof vi.fn>
  }
  toastFn.dismiss = vi.fn()
  toastFn.success = vi.fn()
  toastFn.error = vi.fn()
  return { default: toastFn }
})

import toast from 'react-hot-toast'
import { toastWithUndo } from './undoToast'

const mockedToast = toast as unknown as ReturnType<typeof vi.fn> & {
  dismiss: ReturnType<typeof vi.fn>
  success: ReturnType<typeof vi.fn>
  error: ReturnType<typeof vi.fn>
}

/** Rendert den Toast-Inhalt und liefert den onClick des Rückgängig-Buttons. */
function getUndoHandler(): () => Promise<void> {
  const [render] = mockedToast.mock.calls[mockedToast.mock.calls.length - 1]
  const element = render({ id: 'toast-1' })
  // Struktur: <div><span>msg</span><button onClick=…>Rückgängig</button></div>
  const children = element.props.children
  const button = Array.isArray(children) ? children.find((c: any) => c?.type === 'button') : children
  expect(button?.props?.onClick).toBeTypeOf('function')
  return button.props.onClick
}

describe('toastWithUndo', () => {
  beforeEach(() => {
    mockedToast.mockClear()
    mockedToast.dismiss.mockClear()
    mockedToast.success.mockClear()
    mockedToast.error.mockClear()
  })

  it('zeigt einen Toast mit 8-Sekunden-Fenster', () => {
    toastWithUndo('Status geändert', () => {})
    expect(mockedToast).toHaveBeenCalledTimes(1)
    const [, options] = mockedToast.mock.calls[0]
    expect(options.duration).toBe(8000)
  })

  it('Rückgängig-Klick: schließt den Toast, ruft onUndo, bestätigt', async () => {
    const onUndo = vi.fn().mockResolvedValue(undefined)
    toastWithUndo('Gelöscht', onUndo)
    await getUndoHandler()()
    expect(mockedToast.dismiss).toHaveBeenCalledWith('toast-1')
    expect(onUndo).toHaveBeenCalledTimes(1)
    expect(mockedToast.success).toHaveBeenCalledWith('Rückgängig gemacht.')
    expect(mockedToast.error).not.toHaveBeenCalled()
  })

  it('fehlgeschlagenes Undo meldet einen Fehler-Toast', async () => {
    const onUndo = vi.fn().mockRejectedValue(new Error('kaputt'))
    toastWithUndo('Gelöscht', onUndo)
    await getUndoHandler()()
    expect(mockedToast.error).toHaveBeenCalledWith('Rückgängig machen fehlgeschlagen.')
    expect(mockedToast.success).not.toHaveBeenCalled()
  })

  it('die Nachricht landet im Toast-Inhalt', () => {
    toastWithUndo('Auftrag verschoben.', () => {})
    const [render] = mockedToast.mock.calls[mockedToast.mock.calls.length - 1]
    const element = render({ id: 't' })
    const span = element.props.children.find((c: any) => c?.type === 'span')
    expect(span.props.children).toBe('Auftrag verschoben.')
  })
})
