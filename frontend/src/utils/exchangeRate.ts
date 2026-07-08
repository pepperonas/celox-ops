import { useEffect, useState } from 'react'
import { api } from '../api/client'

// Fallback wenn der Backend-Kurs (EZB via Frankfurter) nicht erreichbar ist.
export const FALLBACK_USD_EUR = 0.92

// Plausibilitätsprüfung — schützt Rechnungsbeträge vor kaputten Upstream-Werten.
export function sanitizeRate(value: unknown): number {
  const rate = Number(value)
  return Number.isFinite(rate) && rate >= 0.5 && rate <= 1.5 ? rate : FALLBACK_USD_EUR
}

let cached: number | null = null
let pending: Promise<number> | null = null

export function getUsdEurRate(): Promise<number> {
  if (cached !== null) return Promise.resolve(cached)
  if (!pending) {
    pending = api
      .get('/token-tracker/exchange-rate')
      .then(r => {
        cached = sanitizeRate(r.data?.rate)
        return cached
      })
      .catch(() => {
        pending = null // nächster Aufruf versucht es erneut
        return FALLBACK_USD_EUR
      })
  }
  return pending
}

/** Liefert sofort den Fallback und aktualisiert auf den Live-Kurs, sobald geladen. */
export function useUsdEurRate(): number {
  const [rate, setRate] = useState<number>(cached ?? FALLBACK_USD_EUR)
  useEffect(() => {
    let mounted = true
    getUsdEurRate().then(r => { if (mounted) setRate(r) })
    return () => { mounted = false }
  }, [])
  return rate
}
