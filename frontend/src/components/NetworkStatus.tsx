import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import Icon from './Icon'

/**
 * Persistent offline banner + transient "back online" toast.
 * Mounted once at the app root; reacts to the browser online/offline events.
 */
export default function NetworkStatus() {
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const goOffline = () => setOffline(true)
    const goOnline = () => {
      setOffline(false)
      toast.success('Wieder online', { id: 'net-status', icon: <Icon name="signal" size={18} /> })
    }
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  if (!offline) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 z-[60] flex items-center justify-center gap-2 bg-warning/90 text-black text-sm font-medium py-2 px-4"
      style={{ top: 'env(safe-area-inset-top, 0px)' }}
    >
      <Icon name="signalOff" size={16} />
      Keine Internetverbindung – Änderungen werden nicht gespeichert.
    </div>
  )
}
