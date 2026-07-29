/**
 * Eigener Icon-Satz — gezeichnet auf dem Material-Raster, nicht zusammengesucht.
 *
 * **Warum überhaupt.** Emojis sind Schrift, keine Icons: sie kommen in der
 * Systemfarbe (ignorieren also unsere Theme-Tokens), sehen auf macOS, Windows und
 * Android völlig unterschiedlich aus, tragen keine Strichbreite und kein Raster,
 * und ihr Screenreader-Name ist der Unicode-Name („Papierkorb", „Bündel
 * Geldscheine") statt der Bedeutung in dieser App.
 *
 * **Das Raster (recherchiert, nicht geraten).** Material-Systemikonen sitzen auf
 * 24×24 dp mit 2 dp Rand, also einer **Live-Area von 20×20**. Alle Striche sind
 * **2 dp** breit — Kurven, Winkel, innen wie außen. Silhouetten bekommen 2 dp
 * Außenradius, Innenecken bleiben scharf. Die Keylines sind Kreis ⌀20,
 * Quadrat 18×18 und Rechteck 20×16 bzw. 16×20; daran orientieren sich die
 * Grundformen hier, damit alle Icons optisch gleich groß wirken.
 * Quellen: m1.material.io/style/icons (Keylines, Strichbreite) und
 * developers.google.com/fonts/docs/material_symbols (Achsen, optische Größen).
 *
 * **Runde Enden und Verbindungen** (`stroke-linecap/linejoin: round`) sind die
 * bewusste Wahl fürs Expressive-Scheme dieses Repos: es arbeitet durchgehend mit
 * großen Radien (`--md-shape-*` bis 28), scharfe Strichenden würden dagegen
 * fremd wirken.
 *
 * **Warum Daten statt fertiges JSX.** So lässt sich der Satz prüfen: ein Test
 * rechnet für JEDES Icon nach, dass keine Koordinate die Live-Area verlässt und
 * die Namen eindeutig sind. Eine Zeichnung, die aus dem Raster fällt, fällt damit
 * beim Testlauf auf und nicht erst im Blick des Nutzers.
 *
 * **Neues Icon:** hier eintragen (Live-Area 2…22, Strich 2), Test läuft mit,
 * dann über `<Icon name="…" />` benutzen. Nie ein Emoji in die UI.
 */

/** Ein Zeichenelement. Bewusst wenige Formen — das hält die Prüfung ehrlich. */
export type IconEl =
  | { t: 'p'; d: string }                                        // Pfad
  | { t: 'c'; cx: number; cy: number; r: number }                // Kreis
  | { t: 'l'; x1: number; y1: number; x2: number; y2: number }   // Linie
  | { t: 'r'; x: number; y: number; w: number; h: number; rx?: number }

export interface IconDef {
  /** Outline-Fassung (Standard) — wird mit Strich gezeichnet. */
  outline: IconEl[]
  /**
   * Gefüllte Fassung für den aktiven Zustand (MD3-`fill`-Achse). Fehlt sie,
   * zeigt `filled` dieselbe Outline — dann trägt allein die Farbe den Zustand.
   */
  solid?: IconEl[]
}

const p = (d: string): IconEl => ({ t: 'p', d })
const c = (cx: number, cy: number, r: number): IconEl => ({ t: 'c', cx, cy, r })
const l = (x1: number, y1: number, x2: number, y2: number): IconEl =>
  ({ t: 'l', x1, y1, x2, y2 })
const r = (x: number, y: number, w: number, h: number, rx = 2): IconEl =>
  ({ t: 'r', x, y, w, h, rx })

// Wiederverwendete Grundformen (Keylines) — halten die optische Größe gleich.
const STAR = 'M12 3.6 14.55 9.4 20.9 10.1 16.1 14.4 17.5 20.6 12 17.4 '
  + '6.5 20.6 7.9 14.4 3.1 10.1 9.45 9.4Z'
const SPARK = 'M12 3.4 13.75 10.25 20.6 12 13.75 13.75 12 20.6 10.25 13.75 '
  + '3.4 12 10.25 10.25Z'

export const ICONS: Record<string, IconDef> = {
  // ---------------------------------------------------------------- KI / Magie
  /** KI-Funktion (war ✨) — großer Funke mit zwei kleinen. */
  sparkle: {
    outline: [
      p('M10 3.2 11.5 8.5 16.8 10 11.5 11.5 10 16.8 8.5 11.5 3.2 10 8.5 8.5Z'),
      p('M18.2 14.2 19 17 21.8 17.8 19 18.6 18.2 21.4 17.4 18.6 14.6 17.8 17.4 17Z'),
    ],
  },
  /** Angereichert (war ✦) — ein einzelner Funke. */
  spark: { outline: [p(SPARK)], solid: [p(SPARK)] },

  // -------------------------------------------------------------- Status/Marken
  /** Warnung (war ⚠) — Dreieck mit Ausruf, Keyline-Dreieck über die Live-Area. */
  warning: {
    outline: [
      p('M12 3.4 21.4 20.6H2.6Z'),
      l(12, 9.6, 12, 14.6),
      c(12, 17.8, 0.35),
    ],
  },
  /** Erfolg/Fertig (war 🎉) — Konfetti-Kegel mit Strahlen. */
  celebrate: {
    outline: [
      p('M3.4 20.6 10.2 8.6 15.4 13.8Z'),
      l(14, 6.2, 15.6, 4.6), l(17.4, 9, 19.6, 8.2), l(17.2, 4.4, 17.9, 2.9),
      c(20.4, 12.2, 0.35), c(12.8, 3.6, 0.35),
    ],
  },
  /** Favorit / gepinnt (war ★ / ☆) — der Zustand steckt in der Füllung. */
  star: { outline: [p(STAR)], solid: [p(STAR)] },
  /** Streak (war 🔥). */
  flame: {
    outline: [
      p('M13.8 2.6C13.8 6.8 8.4 8 8.4 12.8 8.4 14.2 9 15.2 9.8 16 '
        + '8.4 15.6 7.2 14.4 6.8 12.8 6 14 5.6 15.4 5.6 16.8 5.6 19.6 8.4 21.4 '
        + '12 21.4 15.6 21.4 18.4 19 18.4 15.6 18.4 10.2 13.8 8 13.8 2.6Z'),
      p('M12 21.4C10.3 21.4 9.2 20.2 9.2 18.6 9.2 16.8 10.8 16 11.4 13.8 '
        + '12.8 15.2 14.8 16.8 14.8 18.6 14.8 20.2 13.7 21.4 12 21.4Z'),
    ],
    solid: [p('M13.8 2.6C13.8 6.8 8.4 8 8.4 12.8 8.4 14.2 9 15.2 9.8 16 '
      + '8.4 15.6 7.2 14.4 6.8 12.8 6 14 5.6 15.4 5.6 16.8 5.6 19.6 8.4 21.4 '
      + '12 21.4 15.6 21.4 18.4 19 18.4 15.6 18.4 10.2 13.8 8 13.8 2.6Z')],
  },
  /** Freeze-Tage (war 🧊) — Schneeflocke aus drei Achsen. */
  snowflake: {
    outline: [
      l(12, 2.6, 12, 21.4), l(4.1, 7.3, 19.9, 16.7), l(4.1, 16.7, 19.9, 7.3),
      p('M9.4 4.6 12 6.6 14.6 4.6'), p('M9.4 19.4 12 17.4 14.6 19.4'),
    ],
  },

  // ------------------------------------------------------------------- Entitäten
  /** Kunde/Person (war 👤). */
  user: {
    outline: [
      c(12, 8, 4.2),
      p('M4.4 21.2C5.4 16.9 8.4 14.6 12 14.6 15.6 14.6 18.6 16.9 19.6 21.2'),
    ],
    solid: [c(12, 8, 4.2),
      p('M4.4 21.2C5.4 16.9 8.4 14.6 12 14.6 15.6 14.6 18.6 16.9 19.6 21.2Z')],
  },
  /** Mitarbeiterzahl (war 👥). */
  users: {
    outline: [
      c(9.2, 8.4, 3.4), p('M2.6 20.9C3.5 17.2 6 15.4 9.2 15.4 12.4 15.4 14.9 17.2 15.8 20.9'),
      c(16.6, 7.6, 2.6), p('M17.4 15.4C19.3 15.9 20.6 17.7 21.4 20.9'),
    ],
  },
  /** Firma/Kunde (war 🏢). */
  building: {
    outline: [
      r(3.4, 4.2, 9.8, 17.4, 2), r(13.2, 9.4, 7.4, 12.2, 2),
      l(6.4, 8.2, 6.4, 8.2), l(9.6, 8.2, 9.6, 8.2),
      l(6.4, 12.2, 6.4, 12.2), l(9.6, 12.2, 9.6, 12.2),
      l(16.4, 13.4, 16.4, 13.4), l(16.4, 17.2, 16.4, 17.2),
      l(8, 21.6, 8, 17.6),
    ],
  },
  /** Lead / Zielkunde (war 🎯). */
  target: { outline: [c(12, 12, 9.2), c(12, 12, 5), c(12, 12, 1.1)] },
  /** Rechnung (war 🧾) — Belegzettel mit gezacktem Fuß. */
  receipt: {
    outline: [
      p('M5.2 3.4H18.8V20.4L16.4 18.9 14 20.4 11.6 18.9 9.2 20.4 6.8 18.9 5.2 20.4Z'),
      l(8.4, 8, 15.6, 8), l(8.4, 12, 13.4, 12),
    ],
  },
  /** Vertrag/Dokument (war 📄). */
  document: {
    outline: [
      p('M6 2.8H14.4L19 7.4V21.2H6Z'), p('M14.4 2.8V7.4H19'),
      l(9, 12.4, 15.8, 12.4), l(9, 16.4, 13.6, 16.4),
    ],
  },
  /** Auftrag (war 📋) — Klemmbrett. */
  clipboard: {
    outline: [
      r(4.8, 4.4, 14.4, 17, 2.4), r(9, 2.6, 6, 3.6, 1.4),
      l(8.6, 11.6, 15.4, 11.6), l(8.6, 15.6, 13.2, 15.6),
    ],
  },
  /** Website (war 🌐). */
  globe: {
    outline: [
      c(12, 12, 9.2), l(2.8, 12, 21.2, 12),
      p('M12 2.8C14.6 5.4 15.8 8.6 15.8 12 15.8 15.4 14.6 18.6 12 21.2'),
      p('M12 2.8C9.4 5.4 8.2 8.6 8.2 12 8.2 15.4 9.4 18.6 12 21.2'),
    ],
  },
  /** Server / Hosting (war 🖥). */
  server: {
    outline: [
      r(3.4, 4.2, 17.2, 6.4, 1.8), r(3.4, 13.4, 17.2, 6.4, 1.8),
      l(6.6, 7.4, 6.6, 7.4), l(6.6, 16.6, 6.6, 16.6),
      l(10.4, 7.4, 14.6, 7.4), l(10.4, 16.6, 14.6, 16.6),
    ],
  },

  // ------------------------------------------------------------------- Aktionen
  /** Löschen (war 🗑). */
  trash: {
    outline: [
      l(3.4, 6.6, 20.6, 6.6),
      p('M5.8 6.6 7 21.4H17L18.2 6.6'),
      p('M9.4 6.6V4.4C9.4 3.5 10.1 2.8 11 2.8H13C13.9 2.8 14.6 3.5 14.6 4.4V6.6'),
      l(10.4, 10.6, 10.4, 17.6), l(13.6, 10.6, 13.6, 17.6),
    ],
  },
  /** Bearbeiten (war ✏). */
  pencil: {
    outline: [
      p('M4 20 4.7 15.9 16.1 4.5 19.5 7.9 8.1 19.3Z'), l(14.4, 6.2, 17.8, 9.6),
    ],
  },
  /** Suche (war 🔍). */
  search: { outline: [c(10.4, 10.4, 6.6), l(15.2, 15.2, 20.8, 20.8)] },
  /** Einstellungen (war ⚙) — Schieber, im Kleinformat lesbarer als ein Zahnrad. */
  sliders: {
    outline: [
      l(3.2, 7, 20.8, 7), l(3.2, 12, 20.8, 12), l(3.2, 17, 20.8, 17),
      c(8.4, 7, 2), c(15, 12, 2), c(10, 17, 2),
    ],
  },
  /** Schlüssel / Zugang (war 🔑). */
  key: {
    outline: [
      c(8.2, 15.6, 3.8), p('M10.9 12.9 20.4 3.4'), l(17.2, 6.6, 19.8, 9.2),
      l(14.6, 9.2, 17.2, 11.8),
    ],
  },
  /** Kopieren/Neu mischen (war 🎲). */
  dice: {
    outline: [
      r(3.6, 3.6, 16.8, 16.8, 3),
      c(8.4, 8.4, 0.4), c(15.6, 8.4, 0.4), c(12, 12, 0.4),
      c(8.4, 15.6, 0.4), c(15.6, 15.6, 0.4),
    ],
  },
  /** Wiederholen / Follow-up (war 🔁). */
  repeat: {
    outline: [
      p('M4.2 10.4C5.4 6.6 8.6 4.2 12.4 4.2 16 4.2 19 6.4 20.2 9.8'),
      p('M16.8 7 20.4 10.2 17 13.2'),
      p('M19.8 13.6C18.6 17.4 15.4 19.8 11.6 19.8 8 19.8 5 17.6 3.8 14.2'),
      p('M7.2 17 3.6 13.8 7 10.8'),
    ],
  },
  /** Hochladen / Ablegen (war 📥). */
  inbox: {
    outline: [
      p('M3.4 13.4H8L9.6 16.4H14.4L16 13.4H20.6V19.6C20.6 20.6 19.8 21.4 18.8 21.4'
        + 'H5.2C4.2 21.4 3.4 20.6 3.4 19.6Z'),
      l(12, 2.8, 12, 10.8), p('M8.8 7.6 12 10.8 15.2 7.6'),
    ],
  },
  /** Nichts da (war 📭) — offenes, leeres Fach. */
  inboxEmpty: {
    outline: [
      p('M3.4 13.4H8L9.6 16.4H14.4L16 13.4H20.6V19.6C20.6 20.6 19.8 21.4 18.8 21.4'
        + 'H5.2C4.2 21.4 3.4 20.6 3.4 19.6Z'),
      p('M6.6 13.4V6.4C6.6 5.5 7.3 4.8 8.2 4.8H15.8C16.7 4.8 17.4 5.5 17.4 6.4V13.4'),
    ],
  },
  /** Paket / ZIP (war 📦). */
  package: {
    outline: [
      p('M12 2.9 20.8 7.4V16.6L12 21.1 3.2 16.6V7.4Z'),
      p('M3.2 7.4 12 11.9 20.8 7.4'), l(12, 11.9, 12, 21.1),
    ],
  },

  // ------------------------------------------------------------- Kommunikation
  /** E-Mail (war ✉ / 📧). */
  mail: {
    outline: [r(2.8, 5.2, 18.4, 13.6, 2.2), p('M3.4 7 12 13.2 20.6 7')],
  },
  /** Mail raus (war 📬) — Papierflieger. */
  send: {
    outline: [p('M3.2 12.4 20.8 3.6 14.4 21.1 11 13.8Z'), l(11, 13.8, 20.8, 3.6)],
  },
  /** Nachricht (war 💬). */
  chat: {
    outline: [
      r(2.8, 4.4, 18.4, 12.8, 3),
      p('M8 17.2V21.2L12.4 17.2'),
    ],
  },
  /** Telefon (war 📞). */
  phone: {
    outline: [
      p('M6.4 3.6H9.2L10.8 7.8 8.6 9.4C9.8 12.4 11.6 14.2 14.6 15.4L16.2 13.2 '
        + '20.4 14.8V17.6C20.4 19.2 19 20.6 17.4 20.4 10.4 19.6 4.4 13.6 3.6 6.6 '
        + '3.4 5 4.8 3.6 6.4 3.6Z'),
    ],
  },
  /** Online (war 📶) — Funkwellen. */
  signal: {
    outline: [
      l(4.6, 20, 4.6, 16.4), l(9.4, 20, 9.4, 12.6),
      l(14.6, 20, 14.6, 8.4), l(19.4, 20, 19.4, 4.4),
    ],
  },
  /** Offline (war 📡) — Funkwellen mit Strich. */
  signalOff: {
    outline: [
      l(4.6, 20, 4.6, 16.4), l(9.4, 20, 9.4, 12.6),
      l(14.6, 20, 14.6, 8.4), l(19.4, 20, 19.4, 4.4),
      l(3.4, 20.6, 20.6, 3.4),
    ],
  },
  /** LinkedIn / geschäftlich (war 💼). */
  briefcase: {
    outline: [
      r(3, 7.2, 18, 13, 2.2),
      p('M9 7.2V5.2C9 4.4 9.6 3.8 10.4 3.8H13.6C14.4 3.8 15 4.4 15 5.2V7.2'),
      l(3, 12.6, 21, 12.6),
    ],
  },
  /**
   * Vor-Ort-Termin (war 🤝) — bewusst ein Kalender mit Haken.
   *
   * Ein Handschlag ist auf 24 dp mit 2 dp Strich nicht lesbar (zwei verschränkte
   * Hände brauchen mehr Detail als das Raster hergibt) — im ersten Entwurf las er
   * sich als Edelstein. Der Termin ist die Bedeutung, die hier gebraucht wird.
   */
  appointment: {
    outline: [
      r(3.4, 5.4, 17.2, 15.4, 2.6), l(3.4, 10.4, 20.6, 10.4),
      l(8.4, 2.8, 8.4, 6.4), l(15.6, 2.8, 15.6, 6.4),
      p('M8.4 15.4 11.2 18.2 16.4 13'),
    ],
  },

  // --------------------------------------------------------------- Auszeichnung
  /** Abschluss / Gewinn (war 🏆). */
  trophy: {
    outline: [
      p('M7.6 3.4H16.4V9.4C16.4 11.8 14.4 13.8 12 13.8 9.6 13.8 7.6 11.8 7.6 9.4Z'),
      p('M7.6 5.4H4.4V7.4C4.4 9.3 5.9 10.8 7.8 10.9'),
      p('M16.4 5.4H19.6V7.4C19.6 9.3 18.1 10.8 16.2 10.9'),
      l(12, 13.8, 12, 17.4), l(7.6, 20.6, 16.4, 20.6),
      p('M9.4 20.6 10.2 17.4H13.8L14.6 20.6'),
    ],
  },
  /** Traumziel (war 🏁) — Zielflagge. */
  finishFlag: {
    outline: [
      l(5.4, 2.8, 5.4, 21.2),
      p('M5.4 4.2H19.6V12.4H5.4Z'),
      l(12.5, 4.2, 12.5, 12.4), l(5.4, 8.3, 19.6, 8.3),
    ],
    solid: [
      p('M4.4 2.8H6.4V21.2H4.4Z'),
      p('M6.4 4.2H19.6V12.4H6.4Z'),
    ],
  },
  /** Wachstum / Start (war 🚀). */
  rocket: {
    outline: [
      p('M12 2.8C14.9 5.7 16.3 9.3 16.3 13.4L12 16.6 7.7 13.4C7.7 9.3 9.1 5.7 12 2.8Z'),
      c(12, 9.4, 1.9),
      p('M7.7 12.6 5 15.2C4.4 15.8 4.2 16.7 4.5 17.5L5.2 19.6 8.8 17.4'),
      p('M16.3 12.6 19 15.2C19.6 15.8 19.8 16.7 19.5 17.5L18.8 19.6 15.2 17.4'),
      p('M10.4 18.6 12 21.4 13.6 18.6'),
    ],
  },
  /** Geld / Wert (war 💰). */
  coins: {
    outline: [
      c(9.4, 9.4, 5.4), c(14.6, 14.6, 5.4), l(9.4, 6.6, 9.4, 12.2),
    ],
  },
  /** Neue Erkenntnis / Aktion (war ⚡). */
  bolt: { outline: [p('M13.4 2.9 5.9 13.6H11.2L10.6 21.1 18.1 10.4H12.8Z')] },
  /** Ort (war 📍). */
  pin: {
    outline: [
      p('M12 21.2C12 21.2 19 14.4 19 9.7 19 5.8 15.9 2.7 12 2.7 8.1 2.7 5 5.8 '
        + '5 9.7 5 14.4 12 21.2 12 21.2Z'),
      c(12, 9.7, 2.6),
    ],
    solid: [p('M12 21.2C12 21.2 19 14.4 19 9.7 19 5.8 15.9 2.7 12 2.7 8.1 2.7 5 5.8 '
      + '5 9.7 5 14.4 12 21.2 12 21.2Z')],
  },
  /** Erster Eintrag / Aufbau (war 🌱). */
  sprout: {
    outline: [
      l(12, 21.2, 12, 12.4),
      p('M11.6 13C8 13 5 10.2 5 6.4 8.8 6.4 11.6 9.2 11.6 13Z'),
      p('M12.4 15.4C12.4 11.6 15.4 8.8 19 8.8 19 12.6 16.2 15.4 12.4 15.4Z'),
    ],
  },

  // ------------------------------------------------- Traumziel-Objekte (Inhalt)
  /** Geländewagen. */
  suv: {
    outline: [
      p('M3.2 14.4 4.6 9.4H8.2L10 5.8H15.4L17.4 9.4H19.4L20.8 14.4V17.4H3.2Z'),
      c(7.4, 17.4, 2.2), c(16.6, 17.4, 2.2), l(4.6, 11.6, 19.4, 11.6),
    ],
  },
  /** Rennwagen. */
  raceCar: {
    outline: [
      p('M2.8 14.6 5.4 11H9.4L11.4 7.6H15.4L17 11H21.2V15.4H2.8Z'),
      c(7, 17.6, 2.2), c(17, 17.6, 2.2), l(2.8, 9.6, 5.4, 9.6),
    ],
  },
  /** Kraft / Brabus (war 🦍). */
  gorilla: {
    outline: [
      c(12, 13, 6.2),
      c(5.4, 10.6, 1.8), c(18.6, 10.6, 1.8),
      p('M8.6 11.4C9.8 10.2 14.2 10.2 15.4 11.4'),
      c(9.9, 13.2, 0.45), c(14.1, 13.2, 0.45),
      p('M9.2 16.4C10.2 18.2 13.8 18.2 14.8 16.4'),
    ],
  },
  /** Felgen (war 🛞). */
  wheel: {
    outline: [
      c(12, 12, 9.2), c(12, 12, 3.4),
      l(12, 2.8, 12, 8.6), l(12, 15.4, 12, 21.2),
      l(3.9, 8.4, 8.9, 10.9), l(15.1, 13.1, 20.1, 15.6),
      l(20.1, 8.4, 15.1, 10.9), l(8.9, 13.1, 3.9, 15.6),
    ],
  },
  /** Lack & Karosserie (war 🎨). */
  palette: {
    outline: [
      p('M12 2.9C7 2.9 2.9 7 2.9 12 2.9 17 7 21.1 12 21.1 13.6 21.1 14.4 20.1 '
        + '14.4 18.9 14.4 17.3 13.4 16.6 13.4 15.4 13.4 14.2 14.4 13.4 15.8 13.4'
        + 'H18C19.7 13.4 21.1 12 21.1 10.3 21.1 6.1 17.1 2.9 12 2.9Z'),
      c(8, 8.6, 1.3), c(13.4, 7.2, 1.3), c(6.6, 14, 1.3),
    ],
  },
  /** Interieur (war 🪑). */
  seat: {
    outline: [
      p('M7 3.6H17V12.4H7Z'), p('M5.4 12.4H18.6L17.4 17.4H6.6Z'),
      l(7.4, 17.4, 6.6, 21.4), l(16.6, 17.4, 17.4, 21.4),
    ],
  },

  // ------------------------------------------------------ Hinweise & Richtungen
  /** Hinweis (war ⓘ / ℹ️). */
  info: {
    outline: [c(12, 12, 9.2), l(12, 11, 12, 16.6), c(12, 7.9, 0.4)],
    solid: [c(12, 12, 9.2)],
  },
  /** Aufklappen (war ▸ / ▶). */
  chevronRight: { outline: [p('M9.4 4.8 16.6 12 9.4 19.2')] },
  /** Zugeklappt (war ▾). */
  chevronDown: { outline: [p('M4.8 9.4 12 16.6 19.2 9.4')] },
  /** Wieder zuklappen (war ▴). */
  chevronUp: { outline: [p('M4.8 14.6 12 7.4 19.2 14.6')] },
  /** Besser geworden (war ▲). */
  trendUp: { outline: [p('M3.4 17.4 9.4 11.4 13.4 15.4 20.6 8.2'), p('M15.4 8.2H20.6V13.4')] },
  /** Schlechter geworden (war ▼). */
  trendDown: { outline: [p('M3.4 8.2 9.4 14.2 13.4 10.2 20.6 17.4'), p('M15.4 17.4H20.6V12.2')] },
  /** Läuft noch (war ◷). */
  clock: { outline: [c(12, 12, 9.2), p('M12 6.8V12L16 14.4')] },
  // Schließen: symmetrisches Kreuz. Als eigenständige Schaltfläche braucht es ein
  // Icon — ein typografisches ✕ wäre schriftabhängig (Regel in frontend-m3e.md).
  close: { outline: [l(4.8, 4.8, 19.2, 19.2), l(19.2, 4.8, 4.8, 19.2)] },
  // Ziehpunkt: sechs Punkte in zwei Spalten, wie Materials `drag_indicator`. Die
  // Kreise werden gestrichelt gezeichnet (Strich 2 auf Radius 1) — das ergibt
  // optisch den vollen Punkt, ohne eine gefüllte Fassung zu brauchen.
  drag: {
    outline: [
      c(9, 5.5, 1), c(15, 5.5, 1),
      c(9, 12, 1), c(15, 12, 1),
      c(9, 18.5, 1), c(15, 18.5, 1),
    ],
  },
}

/** Alle Icon-Namen — für Tests und Typisierung. */
export type IconName = keyof typeof ICONS
export const ICON_NAMES = Object.keys(ICONS) as IconName[]
