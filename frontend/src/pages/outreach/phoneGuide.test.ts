import { describe, it, expect } from 'vitest'
import { parsePhoneSections } from './PhoneGuide'

describe('parsePhoneSections', () => {
  it('zerlegt an ##-Überschriften, trimmt Text', () => {
    const body = `## Einstieg
Hallo, hier Martin.

## Nutzenargument
Ich spare Zeit.
## Abschluss
15 Minuten?`
    const s = parsePhoneSections(body)
    expect(s.map((x) => x.heading)).toEqual(['Einstieg', 'Nutzenargument', 'Abschluss'])
    expect(s[0].text).toBe('Hallo, hier Martin.')
    expect(s[1].text).toBe('Ich spare Zeit.')
    expect(s[2].text).toBe('15 Minuten?')
  })

  it('kein Heading → leere Liste (Fallback rendert Rohtext)', () => {
    expect(parsePhoneSections('nur ein Fließtext ohne Abschnitte')).toEqual([])
  })

  it('Abschnitt ohne Text bleibt (heading, leerer Text)', () => {
    const s = parsePhoneSections('## Einstieg\n## Abschluss\nText')
    expect(s.map((x) => x.heading)).toEqual(['Einstieg', 'Abschluss'])
    expect(s[0].text).toBe('')
    expect(s[1].text).toBe('Text')
  })

  it('Text vor dem ersten Heading wird verworfen', () => {
    const s = parsePhoneSections('Vorspann\n## Einstieg\nEcht')
    expect(s).toHaveLength(1)
    expect(s[0].heading).toBe('Einstieg')
    expect(s[0].text).toBe('Echt')
  })

  it('mehrzeiliger Abschnittstext bleibt erhalten', () => {
    const s = parsePhoneSections('## Einwandbehandlung\n- A\n- B\n- C')
    expect(s[0].text).toBe('- A\n- B\n- C')
  })
})
