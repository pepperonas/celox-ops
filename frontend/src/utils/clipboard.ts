/**
 * In die Zwischenablage kopieren — mit Fallback für ältere Browser / unsichere
 * Kontexte (kein `navigator.clipboard`). Gibt true bei Erfolg zurück.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* fällt unten auf execCommand zurück */
  }
  let ta: HTMLTextAreaElement | null = null
  let mounted = false
  try {
    ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.top = '-1000px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    mounted = true
    ta.focus()
    ta.select()
    return document.execCommand('copy')
  } catch {
    return false
  } finally {
    // Cleanup IMMER (auch wenn execCommand wirft) — sonst leakt das textarea im DOM.
    if (mounted && ta) document.body.removeChild(ta)
  }
}
