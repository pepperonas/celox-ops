/**
 * Speichert einen Blob als Datei — die EINE Stelle dafür in dieser App.
 *
 * Vorher stand dieser Ablauf zwölfmal kopiert im Code, in zwei Fassungen, und
 * beide trugen dieselben zwei Fehler:
 *
 * 1. **Der Anker hing nicht im Dokument** (in 4 der 12 Fassungen). Chromium
 *    klickt auch einen losen Anker — nachgemessen —, aber das ist Kulanz einer
 *    Engine, nicht die Zusage der Plattform; die anderen 8 Fassungen im selben
 *    Repo hängen ihn ein. Eine App braucht dafür nicht zwei Meinungen.
 * 2. **`revokeObjectURL` lief im selben Tick wie der Klick.** Der Browser liest
 *    den Blob asynchron; nachgemessen ist die URL unmittelbar nach dem Klick
 *    bereits tot. Dass der Download meist trotzdem ankommt, heißt nur, dass der
 *    Wettlauf meist gewonnen wird — auf einem langsamen Gerät, also gerade auf
 *    dem Telefon, ist das keine Grundlage.
 *
 * Der Blob wird bewusst **nicht neu verpackt**: `axios` mit
 * `responseType: 'blob'` liefert den Content-Type des Servers mit, und ein
 * `new Blob([res.data])` warf ihn weg. Ohne Typ rät der Browser — auf iOS
 * bedeutet das, dass ein PDF im Viewer landet statt in den Dateien, mit einem
 * Namen, den niemand vergeben hat.
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Erst freigeben, wenn der Browser gelesen haben kann. Gleiche Frist wie beim
  // PDF-Betrachter im Kundendetail — der Blob hängt bis dahin am Speicher, das
  // ist der Preis dafür, dass der Download nicht abbricht.
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
