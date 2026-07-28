/**
 * Reihenfolge einer Liste einfrieren und Positionswechsel animieren.
 *
 * **Das Problem:** In der To-do-Liste ist der Prioritäts-Punkt ein
 * Durchklick-Schalter (niedrig → normal → hoch). Da die Priorität das zweite
 * Sortierkriterium ist, springt die Zeile beim ersten Klick weg — der Punkt liegt
 * dann nicht mehr unter dem Zeiger und der zweite Klick trifft eine andere Zeile.
 * Das ist nicht nur unruhig, es macht den Schalter unbenutzbar.
 *
 * **Zwei naheliegende Lösungen, beide unbefriedigend:**
 * - Nur animieren: die Zeile gleitet zwar sichtbar, ist aber trotzdem weg.
 * - Erst beim nächsten Seitenaufruf sortieren: dann widerspricht die angezeigte
 *   Reihenfolge unbegrenzt lange der eigenen Sortierregel und sieht kaputt aus.
 *
 * **Deshalb beides, nacheinander:** Während der Nutzer an einer Zeile arbeitet,
 * bleibt die Reihenfolge eingefroren (der Schalter bleibt unter dem Zeiger).
 * Kurz nach dem letzten Klick wird der Frost gelöst und die Zeile gleitet an
 * ihren richtigen Platz — die Bewegung erklärt, was passiert ist, und die Liste
 * bleibt ehrlich sortiert.
 *
 * Hier stehen die reinen Teile (testbar); den DOM-Teil macht `useFlipOrder`.
 */

/**
 * Reihenfolge nach einer eingefrorenen Momentaufnahme herstellen.
 *
 * Elemente aus der Momentaufnahme behalten deren relative Reihenfolge.
 * **Neue** Elemente (nicht in der Aufnahme) bleiben an der Stelle, an die die
 * natürliche Sortierung sie gesetzt hat — ein frisch angelegtes To-do soll nicht
 * ans Ende rutschen, nur weil gerade eine Priorität geändert wurde.
 */
export function applyFrozenOrder<T extends { id: string }>(
  items: T[],
  frozenIds: string[] | null,
): T[] {
  if (!frozenIds || frozenIds.length === 0) return items
  const rank = new Map(frozenIds.map((id, i) => [id, i]))
  // Position in der natürlichen Sortierung als Rückfall für neue Elemente:
  // sie erben den Rang ihres linken Nachbarn und landen damit direkt dahinter.
  const effective = new Map<string, number>()
  let last = -1
  for (const item of items) {
    const known = rank.get(item.id)
    if (known !== undefined) {
      effective.set(item.id, known)
      last = known
    } else {
      effective.set(item.id, last + 0.5)
    }
  }
  return [...items].sort((a, b) =>
    (effective.get(a.id) ?? 0) - (effective.get(b.id) ?? 0))
}

/**
 * Welche Elemente haben sich vertikal bewegt, und um wie viel?
 *
 * Rein, damit die Entscheidung („was wird animiert") ohne DOM prüfbar ist.
 * Zurückgegeben wird die Verschiebung, die eine Zeile *vor* der Animation
 * erhalten muss, um optisch noch an der alten Stelle zu stehen (FLIP).
 */
export function flipDeltas(
  before: Map<string, number>,
  after: Map<string, number>,
  minPixels = 1,
): Array<{ id: string; delta: number }> {
  const out: Array<{ id: string; delta: number }> = []
  for (const [id, top] of after) {
    const old = before.get(id)
    if (old === undefined) continue          // neu eingefügt: nichts zu bewegen
    const delta = old - top
    if (Math.abs(delta) >= minPixels) out.push({ id, delta })
  }
  return out
}

/** Flache Liste von IDs in Anzeigereihenfolge — die Momentaufnahme. */
export function orderSnapshot<T extends { id: string }>(groups: Array<{ items: T[] }>): string[] {
  return groups.flatMap((g) => g.items.map((i) => i.id))
}
