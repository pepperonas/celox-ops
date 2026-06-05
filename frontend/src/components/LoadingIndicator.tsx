interface LoadingIndicatorProps {
  label?: string
  /** Vertical padding of the centered container. */
  className?: string
}

/**
 * MD3 circular loading indicator — centered spinner with optional label.
 * Replaces ad-hoc "Laden..." text across pages.
 */
export default function LoadingIndicator({ label = 'Lädt…', className }: LoadingIndicatorProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-4 py-16 ${className ?? ''}`}>
      <span className="md-spinner" />
      {label && <span className="text-sm text-text-muted animate-md-fade">{label}</span>}
    </div>
  )
}
