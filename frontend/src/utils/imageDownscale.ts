// Screenshots vor dem Upload im Browser verkleinern.
//
// Drei Gründe, das hier statt im Backend zu machen:
//  1. Keine neue Backend-Abhängigkeit (Pillow ist nicht installiert).
//  2. Weniger Upload — ein Handy-Screenshot ist gern 3 MB, verkleinert ~200 KB.
//  3. Das Re-Encode über Canvas **verwirft EXIF** (inklusive GPS-Position) —
//     bei Screenshots aus Kundenchats ein willkommener Nebeneffekt.
//
// Anthropic rechnet Bildkosten aus der Fläche (≈ Breite×Höhe/750 Tokens) und
// skaliert intern auf max. 1568 px lange Kante herunter. Größer hochzuladen
// kostet Übertragung, aber bringt keine Qualität — daher genau dieser Deckel.

export const MAX_EDGE_PX = 1568
export const JPEG_QUALITY = 0.85
/** Muss zur Server-Whitelist passen (services/lead_chat_import.ALLOWED_IMAGE_MIME). */
export const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']

/**
 * Zielmaße bei gleichem Seitenverhältnis. Rein und damit testbar — die Rechnung
 * ist die eigentliche Logik, der Canvas-Teil nur Ausführung.
 * Kleinere Bilder werden NICHT vergrößert.
 */
export function fitWithin(width: number, height: number, maxEdge = MAX_EDGE_PX):
  { width: number; height: number } {
  const longest = Math.max(width, height)
  if (longest <= maxEdge || longest === 0) {
    return { width: Math.round(width), height: Math.round(height) }
  }
  const factor = maxEdge / longest
  return {
    width: Math.max(1, Math.round(width * factor)),
    height: Math.max(1, Math.round(height * factor)),
  }
}

export function isAcceptedImage(file: File): boolean {
  return ACCEPTED_TYPES.includes(file.type)
}

/**
 * Verkleinert das Bild auf die lange Kante `MAX_EDGE_PX` und gibt eine JPEG-Datei
 * zurück. Schlägt irgendein Schritt fehl, kommt die Originaldatei zurück — der
 * Server hat ohnehin harte Grenzen, ein fehlgeschlagener Verkleinerungsversuch
 * darf den Upload nicht verhindern.
 */
export async function downscaleImage(file: File, maxEdge = MAX_EDGE_PX): Promise<File> {
  if (!isAcceptedImage(file)) return file
  try {
    const bitmap = await createImageBitmap(file)
    const { width, height } = fitWithin(bitmap.width, bitmap.height, maxEdge)
    if (width === bitmap.width && height === bitmap.height && file.type === 'image/jpeg') {
      bitmap.close?.()
      return file
    }
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    // Weißer Grund: PNG mit Transparenz würde als JPEG sonst schwarz werden.
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.drawImage(bitmap, 0, 0, width, height)
    bitmap.close?.()

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY))
    if (!blob) return file
    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], name, { type: 'image/jpeg', lastModified: file.lastModified })
  } catch {
    return file
  }
}

/**
 * Wie `downscaleImage`, gibt aber eine JPEG-Data-URL zurück — für Endpoints, die
 * Bilder als JSON erwarten (Lead-Erfassung) statt als multipart.
 * Bei Fehlschlag `null`, damit der Aufrufer das Bild überspringen kann.
 */
export async function downscaleToDataUrl(file: File, maxEdge = MAX_EDGE_PX): Promise<string | null> {
  const shrunk = await downscaleImage(file, maxEdge)
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null)
    reader.onerror = () => resolve(null)
    reader.readAsDataURL(shrunk)
  })
}
