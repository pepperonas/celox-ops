/**
 * Nur `http`/`https` als `href` zulassen.
 *
 * Im Marktradar werden Adressen gerendert, die **nicht** aus dieser App stammen:
 * `ref_url` kommt unverändert aus der importierten Katalogdatei, und die Website eines
 * Referenzkunden ist aus dem HTML einer **fremden Seite** geerntet oder über Google
 * Places aufgelöst.
 *
 * **Was ich gemessen habe, nicht was oft behauptet wird.** Ein `<a
 * href="javascript:…" target="_blank" rel="noopener noreferrer">` führt im heutigen
 * Chromium **nichts** aus: Der Browser blockt Top-Frame-Navigation zu `javascript:`
 * aus einem Link; im Prüfstand öffnete der Klick einen Tab mit Origin `null`, das
 * Skript lief nicht. Die erste Fassung dieses Kommentars behauptete das Gegenteil —
 * das war ungeprüft übernommen.
 *
 * Der Riegel bleibt trotzdem, aus drei Gründen, die alle nicht am Browser hängen:
 *   · Er verlässt sich nicht auf eine **Browser-Schutzmaßnahme** als einzige Grenze.
 *   · Er greift auch dort, wo dieselben Werte NICHT in einem Anker landen —
 *     `window.open(u)` oder ein `location.assign(u)` in künftigem Code.
 *   · Er verhindert einen **toten Link**: Ein unbrauchbarer Wert wird als Text
 *     angezeigt statt als Anker, der ins Nichts führt.
 *
 * Der Weg über die Katalogdatei setzt ohnehin SSH auf dem Server voraus (den
 * HTTP-Upload gibt es nicht mehr) — ein offenes Tor ist das heute also nicht.
 *
 * Rückgabe `undefined` statt einer leeren Zeichenkette: Damit lässt sich am
 * Aufrufort entscheiden, den Link **gar nicht** zu rendern, statt einen toten
 * `<a href="">` zu hinterlassen, der die Seite neu lädt.
 */
export function httpHref(url: string | null | undefined): string | undefined {
  const roh = (url ?? '').trim()
  if (!roh) return undefined
  try {
    // Absolute Adresse verlangen: Ohne Basis wirft `new URL` bei relativen Pfaden,
    // und relative Pfade kommen hier nicht vor — alle Werte sind externe Adressen.
    const u = new URL(roh)
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return undefined
    return u.toString()
  } catch {
    return undefined
  }
}
