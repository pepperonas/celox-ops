import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
// NB: Chart.js registration lives in the chart-using pages (src/utils/charts),
// so the heavy chart bundle code-splits out of the initial load.

// Nach einem Deploy referenziert ein offener Tab noch alte Chunk-Hashes, die
// der Server nicht mehr hat → dynamischer Import (React.lazy-Route) schlägt
// fehl. Vite feuert dafür 'vite:preloadError'; ein einmaliger Reload holt das
// frische Bundle. sessionStorage-Guard verhindert eine Reload-Schleife.
window.addEventListener('vite:preloadError', (event) => {
  const KEY = 'chunk-reload-at'
  const last = Number(sessionStorage.getItem(KEY) || 0)
  if (Date.now() - last > 30_000) {
    event.preventDefault()
    sessionStorage.setItem(KEY, String(Date.now()))
    window.location.reload()
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)

// Register service worker for PWA / "Add to Home Screen"
if ('serviceWorker' in navigator && location.hostname !== 'localhost') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) =>
      console.warn('Service Worker registration failed:', err)
    )
  })
}
