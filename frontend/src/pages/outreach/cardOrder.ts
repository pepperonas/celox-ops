// Reihenfolge der Vorlagen-Karten — reine Logik, damit der schwierige Teil
// geprüft ist.
//
// Der schwierige Teil ist NICHT das Verschieben, sondern das Zurückrechnen: Die
// Reihenfolge gilt je Kanal, gezogen wird aber in einer **gefilterten** Ansicht
// (eine Rubrik, oder ein Suchergebnis). Wer dort eine Karte an Position 2 zieht,
// meint „Platz 2 unter den sichtbaren" — nicht Platz 2 im ganzen Kanal. Die nicht
// sichtbaren Karten müssen ihre Plätze behalten, sonst sortiert ein Filter-Zug
// unbemerkt die ganze Liste um.

/** Verschiebt ein Element; gibt eine neue Liste zurück. */
export function moveItem<T>(list: T[], from: number, to: number): T[] {
  if (from === to) return list
  if (from < 0 || from >= list.length) return list
  const ziel = Math.max(0, Math.min(list.length - 1, to))
  const kopie = [...list]
  const [element] = kopie.splice(from, 1)
  kopie.splice(ziel, 0, element)
  return kopie
}

/** Verschiebt um `delta` Plätze (für die Pfeil-Knöpfe auf Touch-Geräten). */
export function moveBy<T>(list: T[], index: number, delta: number): T[] {
  return moveItem(list, index, index + delta)
}

/**
 * Rechnet eine in der gefilterten Ansicht erzeugte Reihenfolge auf die volle
 * Kanal-Liste zurück.
 *
 * Vorgehen: Die Plätze, die bisher von sichtbaren Karten belegt waren, werden in
 * derselben Folge mit der NEUEN Reihenfolge der sichtbaren Karten aufgefüllt.
 * Alles andere bleibt, wo es war.
 *
 * Beispiel: voll = [A b C d E] (Großbuchstaben sichtbar), neue Sicht = [E A C]
 * → [E b A d C]. b und d liegen unverändert auf Platz 2 und 4.
 */
export function applyVisibleOrder<T extends { id: string }>(
  full: T[],
  visibleInNewOrder: T[],
): T[] {
  const sichtbar = new Set(visibleInNewOrder.map((t) => t.id))
  const nachschub = [...visibleInNewOrder]
  return full.map((eintrag) =>
    sichtbar.has(eintrag.id) ? (nachschub.shift() as T) : eintrag,
  )
}

// Anmerkung zum Ablegen: Ein Zielindex muss NICHT korrigiert werden. `moveItem`
// entfernt das Element zuerst und fügt es dann bei `to` ein — dadurch landet es
// in beiden Richtungen genau auf dem Platz der Karte, auf die man gezogen hat.
// (Eine erste Fassung hatte dafür einen Helfer, dessen beide Zweige identisch
// waren; er ist ersatzlos entfallen.)

/** IDs in Reihenfolge — das, was der Server als neue Ordnung bekommt. */
export function orderIds<T extends { id: string }>(list: T[]): string[] {
  return list.map((t) => t.id)
}
