import { describe, expect, it } from 'vitest'
import { buildSpeakingCard, saetzeVon, stichworte, zeilenVon } from './speakingCard'

const LEITFADEN = `## Einstieg
{{anrede}} {{name}}, Martin Pfeffer von celox.io. Erfasst {{firma}} die Projektzeiten in Projektron BCS?

## Nutzenargument
Zeiterfassung scheitert selten am Willen, sondern am Zeitpunkt.
Das Nachtragen kostet pro Person etwa 15 Minuten am Tag.

## Einwandbehandlung
- „Meine Leute wollen keine Überwachung." → Das Werkzeug läuft lokal und bucht nichts ohne Bestätigung.
- „Zu teuer." → Die Frage ist, was der manuelle Prozess jeden Monat kostet.

## Abschluss
Zwei Wochen Pilot mit drei bis fünf Freiwilligen. Wen hätten Sie dafür im Kopf?`

const MAIL = `{{anrede}} {{name}},

Zeiterfassung scheitert selten am Willen. Sie scheitert am Zeitpunkt.

Ich habe ein Werkzeug gebaut, das die Buchungen aus echter Arbeit ableitet.

Erfassen Sie Ihre Projektzeiten in BCS?`

describe('stichworte', () => {
  it('nimmt die Substantive in Satzreihenfolge — Großschreibung als Signal', () => {
    // Deutsch schreibt Substantive groß; das ist der zuverlässigste maschinelle
    // Hinweis darauf, was die Aussage trägt. Verben und Adverbien („scheitert",
    // „selten") bleiben draußen — sie sagen dem Sprechenden nichts, was er nicht
    // ohnehin formuliert. Reihenfolge des Satzes, nicht nach Häufigkeit.
    expect(stichworte('Zeiterfassung scheitert selten am Willen, sondern am Zeitpunkt.'))
      .toEqual(['Zeiterfassung', 'Willen', 'Zeitpunkt'])
  })

  it('behält Abkürzungen wie BCS trotz Mindestlänge', () => {
    // In der ersten Fassung fiel „BCS" aus dem Einstieg heraus (3 Zeichen), obwohl
    // das ganze Gespräch daran hängt. Live am Leitfaden gesehen.
    expect(stichworte('Erfasst die Firma Projektzeiten in Projektron BCS?')).toContain('BCS')
    expect(stichworte('Wir arbeiten nach ISO 27001 und BSI-Grundschutz.')).toContain('ISO')
  })

  it('lässt den eigenen Namen weg — wer man ist, weiß man', () => {
    expect(stichworte('Martin Pfeffer von celox.io hier, kurz zur Zeiterfassung.'))
      .not.toContain('Pfeffer')
  })

  it('Anrede und Name sind kein Stichwort, die Firma schon', () => {
    // Begrüßung ist Ritual; {{firma}} steht mitten im Satz und muss ersetzt werden.
    const out = stichworte('{{anrede}} {{name}}, erfasst {{firma}} die Projektzeiten?')
    expect(out).not.toContain('[anrede]')
    expect(out).not.toContain('[name]')
    expect(out).toContain('[firma]')
  })

  it('fällt auf gröbere Stichworte zurück, wenn keine Substantive da sind', () => {
    // Lieber mittelmäßige Stichworte als eine leere Zeile.
    expect(stichworte('das wird schneller gehen und besser laufen').length)
      .toBeGreaterThan(1)
  })

  it('wirft Füllwörter und kurze Wörter weg', () => {
    const out = stichworte('Das ist ein Test mit vielen Wörtern')
    expect(out).not.toContain('ist')
    expect(out).not.toContain('ein')
  })

  it('behält Zahlen immer — sie sind das Wertvollste auf der Karte', () => {
    const out = stichworte('Das kostet 15 Minuten am Tag und 3.300 Euro pro Jahr.')
    expect(out).toContain('15')
    expect(out).toContain('3.300')
  })

  it('macht Platzhalter als Lücke sichtbar', () => {
    expect(stichworte('Erfasst {{firma}} die Zeiten?')).toContain('[firma]')
  })

  it('behält Zahlwörter über den Substantiv-Weg', () => {
    expect(stichworte('Das kostet 3.300 Euro pro Person und Jahr.')).toContain('Euro')
  })

  it('entfernt Anführungszeichen und Satzzeichen an den Rändern', () => {
    expect(stichworte('„Überwachung" ist das Thema.')).toContain('Überwachung')
  })

  it('dedupliziert und respektiert das Maximum', () => {
    expect(stichworte('Pilot Pilot Pilot')).toEqual(['Pilot'])
    expect(stichworte('Alpha Beta Gamma Delta Epsilon Zeta Eta Theta', 3)).toHaveLength(3)
  })

  it('liefert bei reinem Füllwort-Satz eine leere Liste statt Unsinn', () => {
    expect(stichworte('Das ist es ja nur.')).toEqual([])
  })
})

describe('saetzeVon', () => {
  it('trennt an Satzzeichen', () => {
    expect(saetzeVon('Erster Satz. Zweiter Satz! Dritter?')).toHaveLength(3)
  })

  it('bricht nicht an Abkürzungen wie „z. B."', () => {
    // Ohne diesen Schutz zerfiele jeder Satz mit einer Abkürzung in Fragmente.
    expect(saetzeVon('Wir prüfen z. B. das Backup und die Zugänge.')).toHaveLength(1)
  })
})

describe('buildSpeakingCard: Telefonleitfaden', () => {
  const karte = buildSpeakingCard(LEITFADEN)

  it('macht aus den Abschnitten den Ablauf', () => {
    expect(karte.schritte.map((s) => s.titel)).toEqual([
      'Einstieg', 'Nutzenargument', 'Abschluss',
    ])
  })

  it('der Einwand-Abschnitt wird KEIN Schritt, sondern Nachschlagewerk', () => {
    // Sonst stünde ein leerer Kasten im Ablauf, und die Einwände lägen im
    // Sprechfluss statt daneben, wo man sie sucht.
    expect(karte.schritte.map((s) => s.titel)).not.toContain('Einwandbehandlung')
    expect(karte.einwaende).toHaveLength(2)
  })

  it('zerlegt Einwände in Einwand, Antwort und Stichworte', () => {
    const [erster] = karte.einwaende
    expect(erster.einwand).toBe('Meine Leute wollen keine Überwachung.')
    expect(erster.antwort).toContain('lokal')
    expect(erster.stichworte).toContain('Werkzeug')
  })

  it('jede Argument-Zeile trägt ihre Stichworte UND ihren Satz', () => {
    // Der Kern des Zeilen-Modells: Stichwort und Satz gehören zusammen. Vorher lagen
    // sie in zwei getrennten Blöcken — man konnte nicht sehen, welches Stichwort zu
    // welchem Satz gehört, und wusste beim Sprechen nicht, wo man ist.
    for (const s of karte.schritte) {
      expect(s.zeilen.length).toBeGreaterThan(0)
      for (const z of s.zeilen) {
        expect(z.satz.length).toBeGreaterThan(0)
        if (!s.wortwoertlich && !z.frage) expect(z.stichworte.length).toBeGreaterThan(0)
      }
    }
  })

  it('der Einstieg steht wörtlich da — ohne Stichworte', () => {
    // Den ersten Satz eines Kaltanrufs improvisiert man nicht. Stichworte wären dort
    // Rauschen in der Sekunde, in der man sie am wenigsten braucht.
    const einstieg = karte.schritte[0]
    expect(einstieg.wortwoertlich).toBe(true)
    expect(einstieg.zeilen.every((z) => z.stichworte.length === 0)).toBe(true)
    expect(einstieg.zeilen.map((z) => z.satz).join(' ')).toContain('Projektron BCS')
  })

  it('nur der Einstieg ist wörtlich, das Argument nicht', () => {
    expect(karte.schritte.filter((s) => s.wortwoertlich)).toHaveLength(1)
  })

  it('Fragen stehen wörtlich statt als Stichwortmüll', () => {
    // „Wen hätten Sie dafür im Kopf?" hat keine brauchbaren Substantive — die
    // Auswahl fiel deshalb auf die gröbere Ebene zurück und lieferte
    // „hätten · dafür · Kopf". Solcher Müll steht neben echten Stichworten und
    // entwertet sie. Live am Leitfaden gesehen.
    const abschluss = karte.schritte[karte.schritte.length - 1]
    const frage = abschluss.zeilen.find((z) => z.frage)
    expect(frage?.satz).toBe('Wen hätten Sie dafür im Kopf?')
    expect(frage?.stichworte).toEqual([])
    // Der Satz VOR der Frage ist Argument und behält seine Stichworte.
    expect(abschluss.zeilen[0].stichworte.length).toBeGreaterThan(0)
  })

  it('nennt die Platzhalter, die man vorher kennen muss', () => {
    expect(karte.platzhalter).toEqual(['anrede', 'name', 'firma'])
  })

  it('hebt die letzte Frage als Abschlussfrage heraus', () => {
    // Die eine Bitte sagt man wörtlich, damit sie knapp und klar bleibt.
    expect(karte.abschlussfrage).toBe('Wen hätten Sie dafür im Kopf?')
  })

  it('Platzhalter erscheinen im Sprechtext als Lücke, nicht als Code', () => {
    const alles = JSON.stringify(karte)
    expect(alles).not.toContain('{{')
    expect(alles).toContain('[firma]')
  })
})

describe('buildSpeakingCard: Leitfaden ohne Abschnitte', () => {
  // Die Karte gibt es nur fuer Telefon, aber ein selbst geschriebener Leitfaden
  // muss keine `##`-Ueberschriften haben — dann tragen die Absaetze den Ablauf.
  const karte = buildSpeakingCard(MAIL)

  it('macht Absätze zu Schritten und benennt den letzten als Abschluss', () => {
    expect(karte.schritte.length).toBeGreaterThanOrEqual(2)
    expect(karte.schritte[karte.schritte.length - 1].titel).toBe('Abschluss')
  })

  it('lässt die Anrede-Zeile weg', () => {
    // „Guten Tag, Frau Meier" muss niemand auf einer Sprechkarte nachlesen.
    expect(karte.schritte[0].titel).toBe('Aufhänger')
    expect(karte.schritte[0].zeilen.map((z) => z.satz).join(' ')).not.toContain('[anrede]')
  })

  it('findet keine Einwände, wo keine stehen', () => {
    expect(karte.einwaende).toEqual([])
  })
})

describe('buildSpeakingCard: Randfälle', () => {
  it('leerer Text ergibt eine leere, aber gültige Karte', () => {
    const karte = buildSpeakingCard('')
    expect(karte.schritte).toEqual([])
    expect(karte.einwaende).toEqual([])
    expect(karte.abschlussfrage).toBeNull()
  })

  it('ein einzelner Satz ohne Struktur ergibt einen Schritt', () => {
    const karte = buildSpeakingCard('Wir sollten kurz sprechen.')
    expect(karte.schritte).toHaveLength(1)
    expect(karte.schritte[0].titel).toBe('Aufhänger')
  })

  it('ein Pfeil ohne Antwort wird nicht zum Einwand', () => {
    const karte = buildSpeakingCard('## A\n- „Nur ein Einwand" →')
    expect(karte.einwaende).toEqual([])
  })
})

describe('Regie-Anweisungen', () => {
  it('eine eingeklammerte Zeile ist Hinweis, nicht Sprechtext', () => {
    // „Gespräch freundlich beenden" sagt man nicht, das tut man. Im Sprechfluss
    // gelesen würde man es versehentlich mitsprechen.
    const karte = buildSpeakingCard(
      '## Einstieg\nArbeiten Sie mit BCS?\n(Wenn nein: freundlich beenden.)',
    )
    expect(karte.schritte[0].hinweis).toBe('Wenn nein: freundlich beenden.')
    expect(karte.schritte[0].zeilen.map((z) => z.satz).join(' ')).not.toContain('beenden')
  })

  it('ein Abschnitt aus NUR einer Regie-Anweisung bleibt erhalten', () => {
    const karte = buildSpeakingCard('## Hinweis\n(Nur bei Bestandskunden anrufen.)')
    expect(karte.schritte).toHaveLength(1)
    expect(karte.schritte[0].hinweis).toContain('Bestandskunden')
    expect(karte.schritte[0].zeilen).toEqual([])
  })
})

describe('Anführungszeichen um den Einwand', () => {
  it('räumt alle vier Varianten ab', () => {
    // Die erste Fassung kannte nur die öffnenden Formen — der deutsche
    // Schlussstrich blieb stehen, und die Anzeige setzte ihren eigenen daneben.
    // Erst im Browser aufgefallen, nicht im Test.
    for (const zeile of [
      '- „Zu teuer.“ → Antwort hier.',
      '- "Zu teuer." → Antwort hier.',
      '- ”Zu teuer.” → Antwort hier.',
      '- Zu teuer. → Antwort hier.',
    ]) {
      const [e] = buildSpeakingCard(`## A\n${zeile}`).einwaende
      expect(e.einwand).toBe('Zu teuer.')
    }
  })
})

describe('zeilenVon', () => {
  it('gibt jedem Satz seine eigenen Stichworte', () => {
    // Kein gemeinsamer Topf mehr: Vorher fraß bei einem langen Abschnitt der Anfang
    // das Kontingent und die Kernaussage am Ende fiel weg (live am überarbeiteten
    // bcsbook-Leitfaden gesehen). Je Satz eine Zeile löst das strukturell — die
    // Sätze konkurrieren nicht mehr um Plätze.
    const zeilen = zeilenVon([
      'Erster Satz mit Alpha Beta Gamma Delta Epsilon.',
      'Dritter Satz mit Kernaussage Kalender Gerüst.',
    ])
    expect(zeilen).toHaveLength(2)
    expect(zeilen[0].stichworte).toContain('Alpha')
    expect(zeilen[1].stichworte).toContain('Kernaussage')
  })

  it('wörtlich heißt: keine Stichworte, nur der Satz', () => {
    const [zeile] = zeilenVon(['Martin Pfeffer von celox.io, kurz zur Zeiterfassung.'], true)
    expect(zeile.stichworte).toEqual([])
    expect(zeile.satz).toContain('Zeiterfassung')
  })

  it('erkennt Fragen auch mit Anführungszeichen dahinter', () => {
    expect(zeilenVon(['Arbeiten Sie mit BCS?'])[0].frage).toBe(true)
    expect(zeilenVon(['Er fragte: „Arbeiten Sie mit BCS?"'])[0].frage).toBe(true)
    expect(zeilenVon(['Das kostet 15 Minuten.'])[0].frage).toBe(false)
  })

  it('macht Platzhalter zur sichtbaren Lücke', () => {
    expect(zeilenVon(['Erfasst {{firma}} die Zeiten in BCS?'])[0].satz).toContain('[firma]')
  })
})

describe('Sprungmarken der Einwände', () => {
  // Ein Leitfaden hat bis zu acht Einwände. Im Gespräch muss man den richtigen in
  // zwei Sekunden finden — acht ausformulierte Zitate liest dafür niemand.
  const karte = buildSpeakingCard(`## Einwandbehandlung
- „Meine Leute wollen keine Überwachung." → Es läuft lokal und bucht nichts ohne Bestätigung.
- „Bei uns arbeitet fast niemand mit Git." → Anwesenheit hat jeder, einen Kalender auch.
- „Woher soll es wissen, an welchem Projekt jemand war?" → Aus dem Kalender, wenn im Termin das Projekt steht.
- „Und wenn der Kalender nicht gepflegt ist?" → Dann bleibt das Gerüst mit Start und Ende.
- „Darf man da überhaupt automatisiert reingehen?" → Es läuft im Browser wie ein Mensch.`)
  const marken = karte.einwaende.map((e) => e.label)

  it('nimmt das Wort, das DIESEN Einwand von den anderen unterscheidet', () => {
    // Der Trick ist die Seltenheit im eigenen Leitfaden: „Kalender" steht in zwei
    // Einwänden und taugt nicht zum Unterscheiden, „Überwachung" und „Git" je
    // einmal — genau daran erkennt man im Gespräch, was man gerade hört.
    expect(marken[0]).toBe('Überwachung')
    expect(marken[1]).toBe('Git')
    expect(marken[2]).toBe('Projekt')
  })

  it('ohne Substantiv ein langes Inhaltswort — kurze Verben sagen nichts', () => {
    // „Darf man da überhaupt automatisiert reingehen?" hat kein Substantiv. Die
    // Grenze bei 11 Zeichen hält „geprüft" oder „machen" draußen: als Sprungmarke
    // wäre das wertlos.
    expect(marken[4]).toBe('automatisiert')
  })

  it('die Marken sind eindeutig — sonst taugen sie nicht zum Springen', () => {
    expect(new Set(marken).size).toBe(marken.length)
  })

  it('Frage- und Verneinungswörter werden keine Marke', () => {
    // Sie stehen groß am Satzanfang und rutschten dadurch als „Substantiv" durch:
    // „Woher" wäre die Marke gewesen, obwohl es um „Projekt" geht.
    for (const m of marken) {
      expect(['Woher', 'Keine', 'Darf', 'Meine', 'Und']).not.toContain(m)
    }
  })

  it('jede Marke ist kurz genug für eine Chipzeile', () => {
    for (const m of marken) expect(m.length).toBeLessThanOrEqual(30)
  })
})

describe('Sprungmarken ohne Substantiv', () => {
  // Über alle 33 Leitfäden gemessen war ein Drittel der Ein-Wort-Marken
  // unbrauchbar („greift", „trifft", „Melde"), weil viele Einwände GAR KEIN
  // Substantiv haben. Bei einem kurzen Einwand ist er selbst die beste Marke.
  const marke = (zeile: string) =>
    buildSpeakingCard(`## Einwandbehandlung\n- ${zeile}`).einwaende[0].label

  it('kurzer Einwand ohne Substantiv wird selbst die Marke', () => {
    expect(marke('„Zu teuer." → Was kostet der manuelle Prozess?')).toBe('Zu teuer')
    expect(marke('„Wir machen das selbst." → Womit genau?')).toBe('Wir machen das selbst')
    expect(marke('„Ist das nötig?" → Seit Juni ist es Pflicht.')).toBe('Ist das nötig')
  })

  it('Großschreibung am Satzanfang ist KEIN Substantiv-Hinweis', () => {
    // Deutsch schreibt das erste Wort immer groß — dort entstanden die falschen
    // Marken „Bisher", „Melde", „Machen", „Läuft" (Verben und Adverbien). Der
    // Verzicht kostet nichts: Die Rückfallstufe beginnt mit genau diesem Wort.
    expect(marke('„Bisher ist nichts passiert." → Das ist der Normalfall.'))
      .toBe('Bisher ist nichts passiert')
    expect(marke('„Machen wir intern." → Wer übernimmt die Haftung?')).toBe('Machen wir intern')
  })

  it('ein Eigenname am Satzanfang zählt trotzdem', () => {
    // Ein innerer Großbuchstabe oder eine Zahl macht ein Wort zum Eigennamen,
    // unabhängig von der Position.
    expect(marke('„NIS2 gilt für uns nicht, wir sind zu klein." → Die Lieferkette zählt mit.'))
      .toBe('NIS2')
  })

  it('die Position stammt aus dem Originalsatz, nicht aus der Filterliste', () => {
    // „Unsere" ist ein Füllwort; nach dem Filtern stünde „Kunden" auf Position 0
    // und wäre als Satzanfang verworfen worden. Beim Messen aufgefallen.
    expect(marke('„Unsere Kunden fragen das nicht." → Noch nicht.')).toBe('Kunden')
  })

  it('langer Einwand ohne Substantiv wird auf Wortgrenze gekürzt', () => {
    // Mitten im Wort abgeschnitten liest sich eine Marke falsch — vorher stand da
    // „Wir haben schon jemand".
    const m = marke('„Wir haben niemanden, der das dauerhaft pflegt." → Genau da komme ich ins Spiel.')
    expect(m.endsWith('…')).toBe(true)
    expect(m.length).toBeLessThanOrEqual(30)
    expect(m).toBe('Wir haben niemanden…')
  })

})

describe('Vorrang beim Kürzen', () => {
  it('Abkürzungen und Zahlen überleben die Obergrenze', () => {
    // Ohne Vorrang schnitt die Grenze bei einem langen Satz genau das
    // Wichtigste weg: „BCS" war das siebte Wort und fiel heraus. Ein Substantiv
    // kann man umschreiben, eine Produktbezeichnung nicht.
    const satz = 'Erfasst die Firma Alpha Beta Gamma Delta Epsilon Zeta in Projektron BCS?'
    const out = stichworte(satz, 5)
    expect(out).toHaveLength(5)
    expect(out).toContain('BCS')
  })

  it('auch Eurozahlen überleben', () => {
    const satz = 'Alpha Beta Gamma Delta Epsilon Zeta Eta kostet 3.300 Euro jährlich.'
    expect(stichworte(satz, 4)).toContain('3.300')
  })

  it('der Vorrang ändert die Reihenfolge nicht', () => {
    const out = stichworte('Alpha Beta Gamma Delta Epsilon in BCS', 3)
    expect(out[out.length - 1]).toBe('BCS')   // steht im Satz zuletzt
  })
})

describe('Sprechkarte nur bei Telefon', () => {
  // Bei E-Mail und LinkedIn schreibt man den Text, man spricht ihn nicht — dort
  // wäre der Knopf ein toter Knopf in jeder Karte. Im Browser über alle drei Kanäle
  // geprüft; dieser Wächter hält es fest.
  //
  // Quelltext-Prüfung, weil es für Komponenten hier keine Testumgebung gibt
  // (kein jsdom, absichtlich). Über `import.meta.glob` wie in `noEmoji.test.ts` —
  // `node:fs` würde `@types/node` erzwingen.
  const dateien = import.meta.glob('./TemplateCard.tsx', {
    query: '?raw', import: 'default', eager: true,
  }) as Record<string, string>
  const quelle = Object.values(dateien)[0] ?? ''

  it('die Quelle wurde wirklich gelesen', () => {
    // Ohne diese Zusicherung wäre der Test unten still grün, falls der Import einen
    // leeren String liefert — genau die Falle, in die der CSS-Token-Test lief.
    expect(quelle.length).toBeGreaterThan(500)
    expect(quelle).toContain('onSpeak')
  })

  it('der Sprechkarten-Knopf hängt am Kanal Telefon', () => {
    expect(quelle).toMatch(/t\.channel === 'phone'[\s\S]{0,400}onSpeak\(t\)/)
  })
})
