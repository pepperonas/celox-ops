import { createPortal } from 'react-dom'

interface FabProps {
  onClick: () => void
  /** When set, renders an extended FAB with this label next to the icon. */
  label?: string
  title?: string
  icon?: React.ReactNode
}

const plusIcon = (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
)

/**
 * MD3 Expressive floating action button — fixed bottom-right, primary-container
 * fill, elevation, state layer + shape-morph on press. Extended when `label` set.
 *
 * Portalt an `document.body`: der Seiten-Wrapper `.page-enter` animiert `transform`
 * und wird dadurch zum Containing Block für `position: fixed` — ohne Portal ankert
 * der FAB an der Inhalts-Unterkante (bei kurzen Seiten mitten im Content) statt am
 * Viewport. Gleicher Gotcha wie bei den Modals.
 */
export default function Fab({ onClick, label, title, icon }: FabProps) {
  return createPortal(
    <button
      onClick={onClick}
      title={title || label}
      aria-label={title || label}
      style={{ bottom: 'max(1.5rem, calc(env(safe-area-inset-bottom) + 0.75rem))' }}
      className={`fab fixed right-5 sm:right-6 z-30 animate-md-pop ${
        label ? 'h-14 px-6 text-sm font-semibold' : 'h-14 w-14'
      }`}
    >
      {icon || plusIcon}
      {label && <span>{label}</span>}
    </button>,
    document.body,
  )
}
