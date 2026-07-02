import type { InvoicePosition } from '../types'

/** Trailing "(YYYY-MM-DD – YYYY-MM-DD)" period stamp of auto-generated KI positions. */
export const PERIOD_SUFFIX = /\(\d{4}-\d{2}-\d{2}\s*[–-]\s*\d{4}-\d{2}-\d{2}\)\s*$/

/**
 * Erkennt automatisch erzeugte KI-Import-Positionen — über das `auto`-Flag (neu)
 * oder Legacy-Muster (Zeitraum-Stempel, Infrastruktur-Zeile, "KI-"-Präfix).
 * So ersetzt ein erneuter Import die Auto-Positionen statt sie zu duplizieren;
 * manuelle Positionen werden nie als auto erkannt.
 */
export function isAutoPosition(p: Pick<InvoicePosition, 'beschreibung' | 'auto'>): boolean {
  if (p.auto === true) return true
  const desc = (p.beschreibung || '').trim()
  if (desc.startsWith('Technische Infrastruktur & externe Systemkosten')) return true
  if (desc.startsWith('KI-')) return true
  return PERIOD_SUFFIX.test(desc)
}
