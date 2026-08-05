import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { saveBlob } from './saveBlob'

/**
 * Handgerollter DOM-Stub statt jsdom (das Repo bleibt abhängigkeitsfrei, die
 * Vitest-Umgebung ist `node`). Er protokolliert die Reihenfolge der Schritte —
 * genau darin lagen die beiden Fehler der zwölf kopierten Fassungen.
 */
type Log = string[]

function installDomStub(log: Log) {
  const anchor: Record<string, unknown> & { click: () => void; remove: () => void } = {
    href: '',
    download: '',
    rel: '',
    connected: false,
    click() {
      log.push(`click(connected=${anchor.connected}, download=${anchor.download})`)
    },
    remove() {
      anchor.connected = false
      log.push('remove')
    },
  }

  const doc = {
    createElement: (tag: string) => {
      log.push(`createElement(${tag})`)
      return anchor
    },
    body: {
      appendChild: (el: typeof anchor) => {
        el.connected = true
        log.push('appendChild')
        return el
      },
    },
  }

  const urlApi = {
    createObjectURL: (blob: Blob) => {
      log.push(`createObjectURL(type=${blob.type || '(leer)'})`)
      return 'blob:stub-1'
    },
    revokeObjectURL: (url: string) => {
      log.push(`revokeObjectURL(${url})`)
    },
  }

  vi.stubGlobal('document', doc)
  vi.stubGlobal('URL', urlApi)
  return { anchor }
}

describe('saveBlob', () => {
  let log: Log

  beforeEach(() => {
    log = []
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('hängt den Anker ins Dokument, BEVOR es klickt', () => {
    installDomStub(log)
    saveBlob(new Blob(['x'], { type: 'application/pdf' }), 'Rechnung.pdf')

    expect(log.indexOf('appendChild')).toBeLessThan(
      log.findIndex((l) => l.startsWith('click(')),
    )
    // Der Klick darf nicht auf einem losen Anker landen.
    expect(log).toContain('click(connected=true, download=Rechnung.pdf)')
  })

  it('gibt die Objekt-URL NICHT im selben Tick frei', () => {
    installDomStub(log)
    saveBlob(new Blob(['x'], { type: 'application/pdf' }), 'Rechnung.pdf')

    // Der eigentliche Regressionsschutz: Wer das alte Muster wieder einbaut
    // (revoke direkt hinter dem Klick), bricht hier.
    expect(log.some((l) => l.startsWith('revokeObjectURL'))).toBe(false)
  })

  it('gibt sie später frei — der Blob soll nicht dauerhaft am Speicher hängen', () => {
    installDomStub(log)
    saveBlob(new Blob(['x']), 'egal.bin')

    vi.advanceTimersByTime(60_000)
    expect(log).toContain('revokeObjectURL(blob:stub-1)')
  })

  it('verpackt den Blob nicht neu — der Content-Type des Servers bleibt', () => {
    installDomStub(log)
    // `new Blob([res.data])` hätte hier '(leer)' protokolliert, und ein Browser
    // ohne Typangabe rät den Umgang mit der Datei.
    saveBlob(new Blob(['%PDF'], { type: 'application/pdf' }), 'Vertrag.pdf')

    expect(log).toContain('createObjectURL(type=application/pdf)')
  })

  it('räumt den Anker wieder ab', () => {
    const { anchor } = installDomStub(log)
    saveBlob(new Blob(['x']), 'egal.bin')

    expect(log).toContain('remove')
    expect(anchor.connected).toBe(false)
  })
})
