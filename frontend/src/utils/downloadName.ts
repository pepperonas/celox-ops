// Download-Dateiname aus dem Content-Disposition-Header lesen (das Backend
// vergibt seit 2026-07 konsistente Namen via services/filenames.py — das
// Frontend soll sie übernehmen statt eigene zu erfinden). Fallback, wenn der
// Header fehlt oder unlesbar ist.

export function filenameFromDisposition(
  disposition: string | null | undefined,
  fallback: string
): string {
  if (!disposition) return fallback

  // RFC 5987: filename*=UTF-8''url-encoded — hat Vorrang vor filename=
  const star = disposition.match(/filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/)
  if (star) {
    try {
      const decoded = decodeURIComponent(star[1].trim())
      if (decoded) return decoded
    } catch {
      // kaputt kodiert → normales filename= versuchen
    }
  }

  const quoted = disposition.match(/filename\s*=\s*"([^"]+)"/)
  const bare = quoted ?? disposition.match(/filename\s*=\s*([^;\s]+)/)
  if (bare?.[1]) {
    try {
      return decodeURIComponent(bare[1])
    } catch {
      return bare[1]
    }
  }
  return fallback
}
