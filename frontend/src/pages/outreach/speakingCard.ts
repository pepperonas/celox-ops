// Sprechkarte: verdichtet eine Vorlage zu einem Gesprächsablauf.
//
// Zweck: im Gespräch NICHT vorlesen. Man braucht Halt, nicht Prosa — also je
// Schritt ein paar Stichworte, an denen man selbst formuliert. Der ganze Satz
// steht klein darunter, als Rettung, wenn der Faden reißt.
//
// Bewusst mechanisch, ohne KI: Die Karte muss beim Klick sofort da sein und darf
// nichts kosten — mitten im Telefonat ist kein Moment für eine Wartezeit oder
// einen Fehlschlag. Die Grenze davon ist ehrlich benannt: Diese Funktion
// verdichtet vorhandene Sätze, sie formuliert nicht neu.
//
// Die Struktur ist da, wo sie zählt, bereits vorhanden: Telefonleitfäden haben
// `## Abschnitt`-Überschriften und Einwände als `- „Einwand" → Antwort`. Genau
// diese beiden Formen tragen den Ablauf.

/** Ein Einwand mit seiner Antwort — im Gespräch ein Nachschlagewerk, kein Text. */
export interface Objection {
  einwand: string
  antwort: string
  /** Stichworte der Antwort — das, was man tatsächlich sagt. */
  stichworte: string[]
}

export interface SpeakingStep {
  /** Überschrift des Schritts, z. B. „Einstieg". */
  titel: string
  /** Stichworte in Reihenfolge der Sätze — die Sprechlinie. */
  stichworte: string[]
  /** Die Sätze selbst, klein darunter, als Rückfallebene. */
  saetze: string[]
  /**
   * Regie-Anweisung in Klammern („Wenn nein: Gespräch freundlich beenden").
   * Bewusst getrennt: Das sagt man NICHT, das tut man. Im Sprechfluss gelesen
   * würde man es versehentlich mitsprechen.
   */
  hinweis?: string
}

export interface SpeakingCard {
  schritte: SpeakingStep[]
  einwaende: Objection[]
  /** Platzhalter, die man vor dem Gespräch kennen muss. */
  platzhalter: string[]
  /** Die Abschlussfrage — der Satz, den man wirklich wörtlich sagen sollte. */
  abschlussfrage: string | null
}

/**
 * Deutsche Funktionswörter. Sie tragen keine Bedeutung, die man sich merken
 * müsste — genau das macht sie zum Ballast auf einer Sprechkarte.
 *
 * Bewusst überschaubar und handverlesen statt eine große Stoppwortliste: zu
 * aggressiv gefiltert bleiben Wortfragmente übrig, die niemand mehr einordnet.
 */
const FUELLWOERTER = new Set([
  'aber', 'alle', 'allen', 'als', 'also', 'am', 'an', 'auch', 'auf', 'aus',
  'bei', 'beim', 'bin', 'bis', 'bist', 'da', 'damit', 'dann', 'das', 'dass',
  'dem', 'den', 'denn', 'der', 'des', 'deshalb', 'die', 'dies', 'diese',
  'diesem', 'diesen', 'dieser', 'doch', 'dort', 'du', 'durch', 'ein', 'eine',
  'einem', 'einen', 'einer', 'eines', 'er', 'es', 'etwas', 'für', 'gar',
  'gegen', 'gibt', 'habe', 'haben', 'hat', 'hatte', 'ich', 'ihm', 'ihn',
  'ihnen', 'ihr', 'ihre', 'ihrem', 'ihren', 'ihrer', 'im', 'in', 'ins', 'ist',
  'ja', 'jede', 'jeden', 'jetzt', 'kann', 'können', 'man', 'mehr', 'mein',
  'mich', 'mir', 'mit', 'nach', 'nein', 'nicht', 'nichts', 'noch', 'nur', 'ob',
  'oder', 'ohne', 'schon', 'sehr', 'sein', 'seine', 'seit', 'sich', 'sie',
  'sind', 'so', 'soll', 'sollen', 'sondern', 'über', 'um', 'und', 'uns',
  'unser', 'unsere', 'vom', 'von', 'vor', 'war', 'waren', 'was', 'wenn',
  'werden', 'wie', 'wir', 'wird', 'wo', 'würde', 'zu', 'zum', 'zur',
])

const PLATZHALTER_RE = /\{\{(\w+)\}\}/g

/** Sichtbare Lücke statt `{{firma}}` — im Gespräch setzt man selbst ein. */
function lueckenText(text: string): string {
  return text.replace(PLATZHALTER_RE, (_, key) => `[${key}]`)
}

/**
 * Der eigene Name und die Firma. Auf der eigenen Sprechkarte ist beides Ballast —
 * wer man ist, weiß man.
 */
const EIGENE_WOERTER = new Set(['martin', 'pfeffer', 'celox.io', 'celox'])

/**
 * Platzhalter, die keine Stichworte verdienen: Anrede und Name sind das immer
 * gleiche Begrüßungsritual und stehen ohnehin auf dem Lead vor einem. `[firma]`
 * dagegen steht mitten im Satz und muss ersetzt werden — das gehört auf die Karte.
 */
const LEISE_PLATZHALTER = new Set(['[anrede]', '[name]'])

/**
 * Stichworte: die inhaltstragenden Wörter, in Satzreihenfolge.
 *
 * **Großschreibung als Signal.** Deutsche Substantive werden großgeschrieben —
 * das ist der zuverlässigste maschinelle Hinweis darauf, was in einem Satz die
 * Aussage trägt. Die erste Fassung nahm einfach die ersten Wörter jedes Satzes;
 * beim Blick auf einen echten Leitfaden kam dabei „Martin · Pfeffer · sonst ·
 * verschwende" heraus, während das entscheidende „BCS" hinten wegfiel. Deutsch
 * stellt die Aussage oft ans Satzende.
 *
 * Funktionswörter am Satzanfang (Dann, Der, Es, Sie) fängt die Füllwortliste ab,
 * weil kleingeschrieben verglichen wird — eine Positionslogik braucht es dafür
 * nicht.
 *
 * Findet der Substantiv-Durchlauf zu wenig, greift der alte, gröbere: lieber
 * mittelmäßige Stichworte als eine leere Zeile.
 */
export function stichworte(satz: string, max = 8): string[] {
  const woerter = lueckenText(satz)
    .split(/[\s—–]+/)
    // Eckige Klammern bleiben stehen: `[firma]` ist die sichtbare Lücke, in die
    // man im Gespräch selbst etwas einsetzt. Als bloßes „firma" wäre nicht mehr
    // erkennbar, dass da etwas fehlt.
    .map((roh) => roh.replace(/^[„"'(]+|[.,;:!?„"')]+$/g, ''))
    .filter(Boolean)

  const brauchbar = (wort: string): boolean => {
    const klein = wort.toLowerCase()
    if (LEISE_PLATZHALTER.has(klein)) return false
    if (EIGENE_WOERTER.has(klein)) return false
    if (/\d/.test(wort)) return true                 // Zahlen immer
    if (/^\[\w+\]$/.test(wort)) return true          // Platzhalter-Lücke
    // Abkürzungen durchgehend groß (BCS, DSB, DSGVO, ISO, BSI). Die Mindestlänge
    // unten hätte sie verschluckt — und gerade sie sind auf einer Sprechkarte
    // unverzichtbar: „BCS" fiel in der ersten Fassung aus dem Einstieg heraus,
    // obwohl das Gespräch genau daran hängt.
    if (/^[A-ZÄÖÜ0-9]{2,}$/.test(wort)) return true
    return wort.length >= 4 && !FUELLWOERTER.has(klein)
  }

  /**
   * Was beim Kürzen überleben MUSS: Abkürzungen, Zahlen, Platzhalter-Lücken.
   *
   * Ohne diesen Vorrang schnitt die Obergrenze bei einem langen Satz genau das
   * Wichtigste weg — im Einstieg des bcsbook-Leitfadens fiel „BCS" heraus, weil
   * es das siebte Wort war. Ein Substantiv kann man im Gespräch umschreiben, eine
   * Produktbezeichnung oder eine Eurozahl nicht.
   */
  const vorrang = (wort: string): boolean =>
    /\d/.test(wort) || /^\[\w+\]$/.test(wort) || /^[A-ZÄÖÜ0-9]{2,}$/.test(wort)

  const sammeln = (nurGross: boolean): string[] => {
    const kandidaten: string[] = []
    for (const wort of woerter) {
      if (!brauchbar(wort)) continue
      if (nurGross && !/^[A-ZÄÖÜ[\d]/.test(wort)) continue
      if (kandidaten.some((w) => w.toLowerCase() === wort.toLowerCase())) continue
      kandidaten.push(wort)
    }
    if (kandidaten.length <= max) return kandidaten
    // Nach Rang auswählen, danach zurück in die Satzreihenfolge sortieren —
    // gesprochen wird entlang des Satzes, nicht entlang der Wichtigkeit.
    return kandidaten
      .map((wort, index) => ({ wort, index, rang: vorrang(wort) ? 0 : 1 }))
      .sort((a, b) => a.rang - b.rang || a.index - b.index)
      .slice(0, max)
      .sort((a, b) => a.index - b.index)
      .map((x) => x.wort)
  }

  const substantive = sammeln(true)
  return substantive.length >= 2 ? substantive : sammeln(false)
}

/**
 * Stichworte eines ganzen Abschnitts — mit einem Kontingent JE SATZ.
 *
 * Ein gemeinsamer Topf nach dem Prinzip „wer zuerst kommt" hat einen Fehler: Wird
 * ein Abschnitt länger, frisst der Anfang das Kontingent und die Aussage am Ende
 * fällt weg. Genau das passierte beim überarbeiteten bcsbook-Leitfaden — die neue
 * Kernaussage (Anwesenheit, Kalender, Gerüst) stand im vierten Satz und
 * verschwand.
 *
 * Also: Jeder Satz bekommt seinen Anteil, mindestens zwei. Die Satzreihenfolge
 * bleibt erhalten — man spricht entlang des Abschnitts, nicht entlang einer
 * Auswahl.
 */
export function abschnittsStichworte(saetze: string[], cap = 12): string[] {
  if (saetze.length === 0) return []
  const quote = Math.max(2, Math.ceil(cap / saetze.length))
  const out: string[] = []
  for (const satz of saetze) {
    for (const w of stichworte(satz, quote)) {
      if (!out.some((x) => x.toLowerCase() === w.toLowerCase())) out.push(w)
    }
  }
  return out.slice(0, cap)
}

/**
 * Abkürzungen, deren Punkt keinen Satz beendet. Ohne diese Liste zerfällt jeder
 * Satz mit „z. B." oder „ca. 15 Minuten" in Fragmente — und Fragmente sind auf
 * einer Sprechkarte schlimmer als ein zu langer Satz.
 */
const ABKUERZUNGEN = [
  'z', 'B', 'u', 'a', 'd', 'h', 'ca', 'bzw', 'ggf', 'evtl', 'inkl', 'exkl',
  'Abs', 'Art', 'Nr', 'Std', 'Min', 'Mio', 'Mrd', 'vgl', 'etc', 'ff', 'Dr',
]
const ABK_RE = new RegExp(`(^|[\\s(„"])(${ABKUERZUNGEN.join('|')})\\.`, 'g')
const PUNKT_MARKER = '\u0001'

/**
 * Zerlegt einen Absatz in Sätze.
 *
 * Zwei Vorsichtsmaßnahmen: Abkürzungspunkte werden vor dem Teilen maskiert, und
 * geteilt wird nur, wenn danach etwas Satzanfängliches steht (Großbuchstabe,
 * Anführung, Zahl). Ein Punkt vor einem Kleinbuchstaben gehört mitten in den
 * Satz — etwa in „celox.io" oder nach einer unbekannten Abkürzung.
 */
export function saetzeVon(text: string): string[] {
  return text
    .replace(ABK_RE, (_, pre: string, abk: string) => `${pre}${abk}${PUNKT_MARKER}`)
    .split(/(?<=[.!?])\s+(?=[A-ZÄÖÜ„"(\d])/)
    .map((s) => s.split(PUNKT_MARKER).join('.').trim())
    .filter((s) => s.length > 2)
}

/** Ist die Zeile ein Einwand-Paar (`- „…" → Antwort`)? */
function alsEinwand(zeile: string): Objection | null {
  if (!zeile.includes('→')) return null
  const ohneBullet = zeile.replace(/^[-•*]\s*/, '')
  const [links, ...rest] = ohneBullet.split('→')
  const antwort = rest.join('→').trim()
  // Alle vier Anführungsvarianten abräumen. Die erste Fassung kannte nur „ und "
  // — der deutsche SCHLUSSstrich “ blieb stehen und die Anzeige zeigte ihn neben
  // ihrem eigenen: „Überwachung.“ ”. Im Browser gesehen.
  const einwand = links.trim().replace(/^[„“”"']+|[„“”"']+$/g, '').trim()
  if (!einwand || !antwort) return null
  return {
    einwand: lueckenText(einwand),
    antwort: lueckenText(antwort),
    stichworte: stichworte(antwort, 7),
  }
}

/** Erster Abschnitt vor der ersten `##`-Überschrift bzw. Absätze ohne Struktur. */
function bloeckeOhneUeberschrift(text: string): string[] {
  return text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean)
}

/**
 * Für E-Mail/LinkedIn: Absätze werden Schritte. Die Benennung folgt dem Aufbau
 * dieser Vorlagen (Aufhänger → Kern → Frage) — mehr als drei Absätze bekommen
 * neutrale Nummern, statt eine Bedeutung zu behaupten, die nicht da ist.
 */
function schritteAusAbsaetzen(bloecke: string[]): SpeakingStep[] {
  const namen = ['Aufhänger', 'Kern', 'Beleg', 'Weiter']
  return bloecke.map((block, i) => {
    const saetze = saetzeVon(block)
    return {
      titel: i === bloecke.length - 1 && bloecke.length > 1
        ? 'Abschluss'
        : namen[i] ?? `Schritt ${i + 1}`,
      stichworte: abschnittsStichworte(saetze, 8),
      saetze: saetze.map(lueckenText),
    }
  })
}

/**
 * Baut die Sprechkarte. Erkennt `##`-Abschnitte (Telefonleitfäden) und fällt
 * sonst auf Absätze zurück.
 *
 * `anrede`/`name` werden aus dem Anfang entfernt: „Guten Tag, Frau Meier" muss
 * niemand auf einer Sprechkarte nachlesen.
 */
export function buildSpeakingCard(body: string): SpeakingCard {
  const text = body.replace(/\r\n/g, '\n').trim()
  const platzhalter = [...new Set(
    [...text.matchAll(PLATZHALTER_RE)].map((m) => m[1]),
  )]

  const hatAbschnitte = /^##\s+/m.test(text)
  const schritte: SpeakingStep[] = []
  const einwaende: Objection[] = []

  if (hatAbschnitte) {
    // An den Überschriften teilen; der Text vor der ersten wird verworfen (bei
    // den Leitfäden ist dort nichts).
    const teile = text.split(/^##\s+/m).slice(1)
    for (const teil of teile) {
      const [kopf, ...restZeilen] = teil.split('\n')
      const zeilen = restZeilen.map((z) => z.trim()).filter(Boolean)
      const saetze: string[] = []
      let hinweis: string | undefined
      for (const zeile of zeilen) {
        const einwand = alsEinwand(zeile)
        if (einwand) {
          einwaende.push(einwand)
          continue
        }
        // Vollständig eingeklammerte Zeile = Regie-Anweisung, kein Sprechtext.
        if (/^\(.*\)$/.test(zeile)) {
          hinweis = lueckenText(zeile.slice(1, -1).trim())
          continue
        }
        saetze.push(...saetzeVon(zeile))
      }
      // Ein Abschnitt, der NUR Einwände enthielt, wird kein Schritt — sonst
      // stünde ein leerer Kasten im Ablauf.
      if (saetze.length === 0 && !hinweis) continue
      // Kontingent je Satz (s. abschnittsStichworte): ein gemeinsamer Topf ließ
      // den Anfang alles fressen — die Kernaussage im vierten Satz fiel weg.
      schritte.push({
        titel: kopf.trim(),
        stichworte: abschnittsStichworte(saetze, 14),
        saetze: saetze.map(lueckenText),
        ...(hinweis ? { hinweis } : {}),
      })
    }
  } else {
    // Anrede-Zeile weg: sie besteht nur aus Platzhaltern.
    const bloecke = bloeckeOhneUeberschrift(text).filter(
      (b, i) => !(i === 0 && /^\{\{anrede\}\}/.test(b)),
    )
    schritte.push(...schritteAusAbsaetzen(bloecke))
  }

  // Die letzte Frage im Text ist der Abschluss — den einen Satz sagt man besser
  // wörtlich, damit die Bitte klar und knapp bleibt.
  const alleFragen = lueckenText(text).match(/[^.!?\n]*\?/g)
  const abschlussfrage = alleFragen?.length
    ? alleFragen[alleFragen.length - 1].trim()
    : null

  return { schritte, einwaende, platzhalter, abschlussfrage }
}
