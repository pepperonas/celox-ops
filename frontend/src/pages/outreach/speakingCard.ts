// Sprechkarte: verdichtet einen TELEFONLEITFADEN zu einem Gesprächsablauf.
//
// **Nur Telefon.** Bei E-Mail und LinkedIn schreibt man den Text, man spricht ihn
// nicht — dort erübrigt sich die Karte, und der Knopf erscheint gar nicht.
//
// Zweck: im Gespräch NICHT vorlesen. Man braucht Halt, nicht Prosa — also je
// SATZ ein paar Stichworte, an denen man selbst formuliert, und den Satz selbst
// klein daneben, als Rettung, wenn der Faden reißt.
//
// **Zwei Arten von Sätzen, und der Unterschied ist der Kern der Karte.** Den
// Einstieg und jede Frage sagt man WÖRTLICH: Der erste Satz eines Kaltanrufs ist
// der eine, den man nicht improvisiert, und eine umformulierte Frage wird
// unpräzise. Alles dazwischen ist Argument — dort trägt das Stichwort, nicht der
// Satz. Stichworte auf dem Einstieg wären reines Rauschen in der Sekunde, in der
// man sie am wenigsten braucht.
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
  /**
   * Ein Wort als Sprungmarke, z. B. „Überwachung", „Git", „Betriebsrat".
   *
   * Ein Leitfaden hat bis zu acht Einwände. Im Gespräch muss man den richtigen in
   * zwei Sekunden finden, und acht ausformulierte Zitate liest man dafür nicht —
   * ein Wort erkennt man im Vorbeischauen.
   */
  label: string
}

/**
 * Eine Sprechzeile: ein Satz mit seinen eigenen Stichworten.
 *
 * **Warum je Satz und nicht je Abschnitt.** Vorher lagen die Stichworte eines
 * Abschnitts in EINER Reihe und die Sätze in einer zweiten Liste darunter. Am
 * echten Leitfaden waren das 14 Wörter in einer Zeile — eine Wortwolke, aus der
 * nicht hervorgeht, welches Stichwort zu welchem Satz gehört. Damit weiß man beim
 * Sprechen nie, wo man ist. Gepaart ist beides eine Sprechlinie, an der man
 * entlanggeht.
 *
 * Nebeneffekt: Das Kontingent-Problem entfällt strukturell. Ein gemeinsamer Topf
 * ließ den Anfang alles fressen (die Kernaussage im vierten Satz fiel weg), was
 * eine Quote je Satz reparieren musste — jetzt konkurrieren die Sätze nicht mehr.
 */
export interface SpeakingLine {
  /** Der Satz. Bei `wortwoertlich` das, was man sagt; sonst die Rückfallebene. */
  satz: string
  /** Stichworte, an denen man formuliert. LEER, wenn der Satz wörtlich gehört. */
  stichworte: string[]
  /** Frage? Fragen sagt man wörtlich — umformuliert werden sie unpräzise. */
  frage: boolean
}

export interface SpeakingStep {
  /** Überschrift des Schritts, z. B. „Einstieg". */
  titel: string
  /** Die Sprechlinien in Satzreihenfolge. */
  zeilen: SpeakingLine[]
  /**
   * Wörtlich sprechen statt improvisieren — gilt für den Einstieg. Der erste Satz
   * eines Kaltanrufs entscheidet, ob es die nächsten zwei Minuten gibt; dort
   * braucht man den Satz, nicht Stichworte.
   */
  wortwoertlich?: boolean
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
  // Frage- und Verneinungswörter. Sie stehen groß am Satzanfang und rutschten
  // dadurch als „Substantiv" durch — auf einer Sprechmarke wäre „Woher" das
  // Stichwort gewesen, obwohl es um „Projekt" geht.
  'keine', 'keinen', 'keiner', 'kein', 'warum', 'weshalb', 'wieso', 'woher',
  'wann', 'welche', 'welchem', 'welchen', 'welcher', 'wer', 'wen', 'wem',
  'wessen', 'wohin', 'weswegen', 'wollen', 'will', 'darf', 'dürfen', 'muss',
  'müssen', 'sollte', 'sollten', 'gerade', 'jemand', 'jemanden', 'meine',
  'meinen', 'meiner',
  // Pronominaladverbien und Satzverbinder. Sie stehen fast immer GROSS am
  // Satzanfang und rutschten dadurch als „Substantiv" durch — im Nutzenargument
  // war „Daraus" das erste Stichwort einer Zeile, in der es um „Gerüst" geht.
  // Anders als bei den Sprungmarken kann man hier nicht einfach das erste Wort
  // verwerfen: „Zeiterfassung scheitert nicht am Willen" beginnt mit dem
  // Stichwort. Also die Wortart benennen, nicht die Position.
  'daraus', 'dadurch', 'darin', 'dafür', 'dazu', 'dabei', 'danach', 'davor',
  'deswegen', 'trotzdem', 'außerdem', 'zusätzlich', 'übrigens', 'bisher',
  'genau', 'sonst', 'zudem', 'hätten', 'hatten', 'wären', 'würden', 'lassen',
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

/** Endet der Satz mit einem Fragezeichen? */
function istFrage(satz: string): boolean {
  return /\?["„“”']*\s*$/.test(satz.trim())
}

/**
 * Sätze zu Sprechzeilen: je Satz eigene Stichworte.
 *
 * **Leere Stichworte heißen: den Satz sprechen.** Drei Fälle:
 *   · der Einstieg (`wortwoertlich`) — den improvisiert man nicht,
 *   · jede Frage — umformuliert wird sie unpräzise,
 *   · und ein Satz, aus dem sich nichts Brauchbares gewinnen lässt.
 *
 * Der dritte Fall ist gemessen, nicht vermutet: Über alle 33 Leitfäden waren 45
 * von 505 Stichworten kleingeschrieben — dort hatte der gröbere Rückfall gegriffen
 * und lieferte „statt · fast · immer · kommt · sieht". Solcher Müll steht neben
 * echten Stichworten und entwertet sie. Ein substantivarmer Satz („Dann rechnen
 * wir.") lässt sich nicht verdichten, also bleibt er, wie er ist — das ist keine
 * Notlösung, sondern die richtige Darstellung.
 *
 * Die Schwelle: mindestens zwei Stichworte, und mindestens eines muss ein
 * Substantiv, eine Zahl oder eine Platzhalter-Lücke sein. Ein einzelnes Wort ist
 * keine Sprechlinie, und eine Reihe aus Verben sagt weniger als der Satz selbst.
 */
export function zeilenVon(saetze: string[], wortwoertlich = false): SpeakingLine[] {
  return saetze.map((satz) => {
    const frage = istFrage(satz)
    const roh = frage || wortwoertlich ? [] : stichworte(satz, 6)
    const traegt = roh.length >= 2 && roh.some((w) => /^[A-ZÄÖÜ[\d]/.test(w))
    return {
      satz: lueckenText(satz),
      frage,
      stichworte: traegt ? roh : [],
    }
  })
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
    label: '',   // wird gesetzt, sobald alle Einwände bekannt sind (s. setzeLabels)
  }
}

/** Satzzeichen und Anführungen am Rand weg — der Kern des Einwands. */
function kern(einwand: string): string {
  return einwand.replace(/^[„“”"']+/, '').replace(/[.?!…„“”"'\s]+$/, '')
}

/** Auf Wortgrenze kürzen. Ein mitten im Wort abgeschnittenes Label liest sich falsch. */
function kuerze(text: string, max: number): string {
  if (text.length <= max) return text
  const schnitt = text.slice(0, max)
  const luecke = schnitt.lastIndexOf(' ')
  const basis = luecke > max * 0.5 ? schnitt.slice(0, luecke) : schnitt
  return `${basis.replace(/[,;:]$/, '')}…`
}

/** Wie lang darf eine Marke sein, damit sie im Vorbeischauen erfassbar bleibt? */
const MARKE_MAX = 30

/**
 * Sprungmarken für die Einwände: das, woran man im Gespräch erkennt, welchen
 * Einwand man gerade hört.
 *
 * Ein Leitfaden hat bis zu acht Einwände. Den richtigen muss man in zwei Sekunden
 * finden, und acht ausformulierte Zitate liest dafür niemand.
 *
 * **Vier Stufen, in dieser Reihenfolge — und die Reihenfolge ist die eigentliche
 * Erkenntnis.** Der erste Entwurf nahm immer ein Einzelwort; über alle 33 Leitfäden
 * gesehen war ein Drittel davon unbrauchbar („greift", „trifft", „Melde"), weil
 * viele Einwände GAR KEIN Substantiv haben:
 *
 *   1. Das unterscheidende Substantiv, wenn es eins gibt: „Überwachung", „Git",
 *      „Betriebsrat", „IT-Entscheidung". Ein Wort erkennt man schneller als einen
 *      Satz — deshalb steht diese Stufe vor der nächsten, auch bei kurzen
 *      Einwänden („Und der Betriebsrat?" wird „Betriebsrat", nicht „Und der …").
 *   2. Sonst der Einwand selbst, wenn er kurz ist: „Zu teuer", „Wir sind zu klein",
 *      „Ist das nötig?". Kürzer geht es nicht, und als Marke ist er perfekt.
 *   3. Sonst ein langes Inhaltswort (ab 11 Zeichen): „automatisiert". Kurze Verben
 *      sind hier bewusst ausgeschlossen — „geprüft" oder „machen" sagt nichts.
 *   4. Sonst der gekürzte Einwand. Eine Phrase ist immer noch erkennbar, ein
 *      zufälliges Verb nicht.
 *
 * Die Seltenheit auf Stufe 1 ist der Trick: „Kalender" steht in mehreren Einwänden
 * und taugt deshalb nicht zum Unterscheiden, „Git" genau einmal.
 */
function setzeLabels(einwaende: Objection[]): void {
  /**
   * Wörter mit der Angabe, ob sie am SATZANFANG standen.
   *
   * Die Position muss aus dem Originalsatz kommen, nicht aus der gefilterten Liste:
   * In „Unsere Kunden fragen das nicht." ist „Unsere" ein Füllwort — nach dem
   * Filtern stünde „Kunden" auf Position 0 und wäre als Satzanfang verworfen
   * worden. Die gute Marke „Kunden" wäre still verloren gegangen (beim Messen über
   * alle 33 Leitfäden aufgefallen).
   */
  const woerterVon = (text: string): { wort: string; anfang: boolean }[] =>
    text.split(/[\s—–]+/)
      .map((w, i) => ({ wort: w.replace(/^[„“”"'(]+|[.,;:!?„“”"')]+$/g, ''), anfang: i === 0 }))
      .filter(({ wort }) => wort.length >= 3 && !FUELLWOERTER.has(wort.toLowerCase()))

  /**
   * Am Satzanfang ist Großschreibung KEIN Hinweis auf ein Substantiv — Deutsch
   * schreibt das erste Wort immer groß. Genau dort entstanden die vier falschen
   * Marken „Bisher", „Melde", „Machen", „Läuft" (alles Verben und Adverbien).
   *
   * Verworfen wird das erste Wort deshalb als Substantiv-Kandidat, es sei denn, es
   * trägt einen inneren Großbuchstaben oder eine Zahl: „NIS2", „IT-Firma",
   * „Cyber-Versicherung" sind Eigennamen, unabhängig von der Position.
   *
   * Der Verzicht kostet nichts: Beide Rückfallstufen (kurzer Einwand, gekürzte
   * Phrase) BEGINNEN mit genau diesem Wort — „Budget ist eingefroren…" führt das
   * Budget also weiter vorn als eine Ein-Wort-Marke.
   */
  const eigenname = (wort: string): boolean => /[A-ZÄÖÜ0-9]/.test(wort.slice(1))

  // In wie vielen Einwänden kommt ein Wort vor?
  const haeufigkeit = new Map<string, number>()
  for (const e of einwaende) {
    for (const w of new Set(woerterVon(e.einwand).map((x) => x.wort.toLowerCase()))) {
      haeufigkeit.set(w, (haeufigkeit.get(w) ?? 0) + 1)
    }
  }

  // Seltenstes zuerst; bei Gleichstand das längere (spezifischer), dann das frühere
  // — eine feste Ordnung, damit die Marke nicht zufällig wirkt.
  const bestes = (woerter: { wort: string }[]): string | null => woerter
    .map(({ wort }, index) => ({
      wort,
      index,
      df: haeufigkeit.get(wort.toLowerCase()) ?? 1,
      laenge: wort.length,
    }))
    .sort((a, b) => a.df - b.df || b.laenge - a.laenge || a.index - b.index)[0]?.wort ?? null

  for (const e of einwaende) {
    const woerter = woerterVon(e.einwand)
    const text = kern(e.einwand)
    // Großgeschrieben ab DREI Zeichen: „Git" ist der ganze Einwand, fiel aber bei
    // einer Mindestlänge von 4 durch — und die Marke wurde „arbeitet". Dieselbe
    // Falle wie damals bei „BCS". Kurze Funktionswörter (Und, Der, Was, Darf)
    // fängt die Füllwortliste ab, dafür braucht es keine Längengrenze.
    const substantiv = bestes(woerter.filter(({ wort, anfang }) =>
      /^[A-ZÄÖÜ]/.test(wort) && wort.length >= 3 && (!anfang || eigenname(wort))))
    if (substantiv) { e.label = substantiv; continue }
    if (text.length <= MARKE_MAX) { e.label = text; continue }
    const langesWort = bestes(woerter.filter(({ wort }) => wort.length >= 11))
    e.label = langesWort ?? kuerze(text, MARKE_MAX - 6)
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
      // Der erste Absatz IST der Einstieg, auch ohne Überschrift.
      zeilen: zeilenVon(saetze, i === 0),
      ...(i === 0 ? { wortwoertlich: true } : {}),
    }
  })
}

/**
 * Abschnitte, die man wörtlich spricht. Alle 33 Leitfäden im Bestand beginnen mit
 * `## Einstieg`; die Alternativen stehen für selbst geschriebene Vorlagen. Bewusst
 * am Titel erkannt und nicht an der Position: Ein Leitfaden, der mit „## Ziel des
 * Gesprächs" anfängt, hätte sonst eine Notiz an sich selbst als Sprechtext.
 */
const EINSTIEG_RE = /^(einstieg|gesprächseinstieg|eröffnung|begrüßung|aufhänger)\b/i

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
      const titel = kopf.trim()
      const wortwoertlich = EINSTIEG_RE.test(titel)
      schritte.push({
        titel,
        zeilen: zeilenVon(saetze, wortwoertlich),
        ...(wortwoertlich ? { wortwoertlich: true } : {}),
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

  // Sprungmarken erst jetzt: Sie hängen davon ab, welche Wörter in den ANDEREN
  // Einwänden vorkommen.
  setzeLabels(einwaende)

  // Die letzte Frage im Text ist der Abschluss — den einen Satz sagt man besser
  // wörtlich, damit die Bitte klar und knapp bleibt.
  const alleFragen = lueckenText(text).match(/[^.!?\n]*\?/g)
  const abschlussfrage = alleFragen?.length
    ? alleFragen[alleFragen.length - 1].trim()
    : null

  return { schritte, einwaende, platzhalter, abschlussfrage }
}
