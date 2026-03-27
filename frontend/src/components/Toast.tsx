import { Toaster } from 'react-hot-toast'

export default function Toast() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#1f2937',
          color: '#f3f4f6',
          border: '1px solid #374151',
          borderRadius: '0.75rem',
        },
        success: {
          iconTheme: {
            primary: '#00b4d8',
            secondary: '#f3f4f6',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444',
            secondary: '#f3f4f6',
          },
        },
      }}
    />
  )
}
