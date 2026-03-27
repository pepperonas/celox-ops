import { Toaster } from 'react-hot-toast'

export default function Toast() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#161b22',
          color: '#e6edf3',
          border: '1px solid #30363d',
          borderRadius: '12px',
        },
        success: {
          iconTheme: {
            primary: '#3fb950',
            secondary: '#e6edf3',
          },
        },
        error: {
          iconTheme: {
            primary: '#f85149',
            secondary: '#e6edf3',
          },
        },
      }}
    />
  )
}
