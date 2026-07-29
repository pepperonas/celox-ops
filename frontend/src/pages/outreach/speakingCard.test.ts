import { describe, expect, it } from 'vitest'
import { buildSpeakingCard, saetzeVon, stichworte } from './speakingCard'

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

  it('jeder Schritt hat Stichworte UND die Sätze als Rückfallebene', () => {
    for (const s of karte.schritte) {
      expect(s.stichworte.length).toBeGreaterThan(0)
      expect(s.saetze.length).toBeGreaterThan(0)
    }
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

describe('buildSpeakingCard: E-Mail ohne Abschnitte', () => {
  const karte = buildSpeakingCard(MAIL)

  it('macht Absätze zu Schritten und benennt den letzten als Abschluss', () => {
    expect(karte.schritte.length).toBeGreaterThanOrEqual(2)
    expect(karte.schritte[karte.schritte.length - 1].titel).toBe('Abschluss')
  })

  it('lässt die Anrede-Zeile weg', () => {
    // „Guten Tag, Frau Meier" muss niemand auf einer Sprechkarte nachlesen.
    expect(karte.schritte[0].titel).toBe('Aufhänger')
    expect(karte.schritte[0].saetze.join(' ')).not.toContain('[anrede]')
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
    expect(karte.schritte[0].saetze.join(' ')).not.toContain('beenden')
  })

  it('ein Abschnitt aus NUR einer Regie-Anweisung bleibt erhalten', () => {
    const karte = buildSpeakingCard('## Hinweis\n(Nur bei Bestandskunden anrufen.)')
    expect(karte.schritte).toHaveLength(1)
    expect(karte.schritte[0].hinweis).toContain('Bestandskunden')
    expect(karte.schritte[0].saetze).toEqual([])
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
