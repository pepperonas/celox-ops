import { Toaster } from 'react-hot-toast'

export default function Toast() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: 'var(--md-surface-container-highest)',
          color: 'var(--text)',
          border: 'none',
          borderRadius: 'var(--md-shape-md)',
          boxShadow: 'var(--md-elev-3)',
          fontSize: '13px',
          padding: '12px 16px',
        },
        success: {
          iconTheme: {
            primary: 'var(--md-success)',
            secondary: 'var(--md-surface-container-highest)',
          },
        },
        error: {
          iconTheme: {
            primary: 'var(--md-error)',
            secondary: 'var(--md-surface-container-highest)',
          },
        },
      }}
    />
  )
}
