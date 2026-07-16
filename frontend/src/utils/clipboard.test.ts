import { describe, it, expect, vi, afterEach } from 'vitest'
import { copyText } from './clipboard'

/**
 * vitest läuft hier im node-Env (kein jsdom) → wir stubben die benötigten
 * DOM/Browser-Globals minimal mit vi.stubGlobal. So testen wir die Zweig-Logik
 * (Clipboard-API vs. execCommand-Fallback) und das textarea-Cleanup ohne echte DOM.
 */
interface FakeTextarea {
  value: string
  style: Record<string, string>
  setAttribute: ReturnType<typeof vi.fn>
  focus: ReturnType<typeof vi.fn>
  select: ReturnType<typeof vi.fn>
}

function setup(opts: {
  secure?: boolean
  clipboard?: { writeText: ReturnType<typeof vi.fn> } | null
  execResult?: boolean
  execThrows?: boolean
  appendThrows?: boolean
}) {
  const appended: FakeTextarea[] = []
  const removed: FakeTextarea[] = []
  const created: FakeTextarea[] = []

  const createElement = vi.fn(() => {
    const ta: FakeTextarea = {
      value: '',
      style: {},
      setAttribute: vi.fn(),
      focus: vi.fn(),
      select: vi.fn(),
    }
    created.push(ta)
    return ta
  })
  const execCommand = vi.fn(() => {
    if (opts.execThrows) throw new Error('execCommand nicht verfügbar')
    return opts.execResult ?? true
  })

  vi.stubGlobal('document', {
    createElement,
    execCommand,
    body: {
      appendChild: vi.fn((el: FakeTextarea) => {
        if (opts.appendThrows) throw new Error('appendChild failed')
        appended.push(el)
      }),
      removeChild: vi.fn((el: FakeTextarea) => { removed.push(el) }),
    },
  })
  vi.stubGlobal('window', { isSecureContext: opts.secure ?? true })
  vi.stubGlobal('navigator', { clipboard: opts.clipboard ?? undefined })

  return { appended, removed, created, createElement, execCommand }
}

afterEach(() => vi.unstubAllGlobals())

// ---- Happy path -----------------------------------------------------------
describe('copyText – Happy path', () => {
  it('kopiert im sicheren Kontext über navigator.clipboard und meldet Erfolg', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const h = setup({ secure: true, clipboard: { writeText } })

    const ok = await copyText('Hallo Welt')

    expect(ok).toBe(true)
    expect(writeText).toHaveBeenCalledWith('Hallo Welt')
    expect(h.createElement).not.toHaveBeenCalled() // kein Fallback → kein DOM-Element
  })

  it('nutzt bei jedem Aufruf den exakten Text (kein Trimmen/Verändern)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    setup({ clipboard: { writeText } })
    await copyText('  {{name}} — üäö 🚀  ')
    expect(writeText).toHaveBeenCalledWith('  {{name}} — üäö 🚀  ')
  })
})

// ---- Edge cases -----------------------------------------------------------
describe('copyText – Edge cases', () => {
  it('leerer String wird als Erfolg kopiert', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    setup({ clipboard: { writeText } })
    expect(await copyText('')).toBe(true)
    expect(writeText).toHaveBeenCalledWith('')
  })

  it('sehr langer Unicode-Text geht unverändert an den Fallback (execCommand)', async () => {
    const long = '😀'.repeat(10_000)
    const h = setup({ clipboard: null, execResult: true }) // kein clipboard → Fallback
    const ok = await copyText(long)
    expect(ok).toBe(true)
    expect(h.created[0].value).toBe(long)
  })
})

// ---- Failure modes --------------------------------------------------------
describe('copyText – Failure modes', () => {
  it('Clipboard-API wirft → execCommand-Fallback greift und meldet Erfolg', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('permission denied'))
    const h = setup({ secure: true, clipboard: { writeText }, execResult: true })

    const ok = await copyText('X')

    expect(ok).toBe(true)
    expect(writeText).toHaveBeenCalled()
    expect(h.execCommand).toHaveBeenCalledWith('copy')
    expect(h.created[0].value).toBe('X')
  })

  it('unsicherer Kontext (isSecureContext=false) → direkt Fallback, Clipboard-API ungenutzt', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const h = setup({ secure: false, clipboard: { writeText }, execResult: true })

    await copyText('X')

    expect(writeText).not.toHaveBeenCalled()
    expect(h.execCommand).toHaveBeenCalled()
  })

  it('kein navigator.clipboard vorhanden → Fallback', async () => {
    const h = setup({ clipboard: null, execResult: true })
    expect(await copyText('X')).toBe(true)
    expect(h.execCommand).toHaveBeenCalled()
  })

  it('beide Wege scheitern (execCommand=false) → false', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('nope'))
    setup({ clipboard: { writeText }, execResult: false })
    expect(await copyText('X')).toBe(false)
  })

  it('execCommand wirft → false statt Crash', async () => {
    setup({ clipboard: null, execThrows: true })
    expect(await copyText('X')).toBe(false)
  })
})

// ---- State / Cleanup ------------------------------------------------------
describe('copyText – State & Cleanup', () => {
  it('Fallback entfernt das textarea wieder (append == remove, gleiches Element)', async () => {
    const h = setup({ clipboard: null, execResult: true })
    await copyText('X')
    expect(h.appended).toHaveLength(1)
    expect(h.removed).toHaveLength(1)
    expect(h.removed[0]).toBe(h.appended[0])
  })

  it('räumt das textarea auch bei execCommand=false auf (kein Leak)', async () => {
    const h = setup({ clipboard: null, execResult: false })
    await copyText('X')
    expect(h.removed).toHaveLength(1)
  })

  it('räumt das textarea auch auf, wenn execCommand WIRFT (Regression: finally-Cleanup)', async () => {
    const h = setup({ clipboard: null, execThrows: true })
    await copyText('X')
    expect(h.appended).toHaveLength(1)
    expect(h.removed).toHaveLength(1) // ohne finally-Fix würde das textarea leaken
  })

  it('scheitert appendChild, wird nichts entfernt (kein removeChild auf Nicht-Angehängtem)', async () => {
    const h = setup({ clipboard: null, appendThrows: true })
    expect(await copyText('X')).toBe(false)
    expect(h.removed).toHaveLength(0)
  })

  it('Happy-Path erzeugt kein textarea (kein DOM-Müll)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const h = setup({ clipboard: { writeText } })
    await copyText('X')
    expect(h.created).toHaveLength(0)
  })
})

// ---- Concurrency ----------------------------------------------------------
describe('copyText – Concurrency', () => {
  it('zwei gleichzeitige Fallback-Kopien räumen beide ihr eigenes textarea auf', async () => {
    const h = setup({ clipboard: null, execResult: true })
    const results = await Promise.all([copyText('A'), copyText('B')])
    expect(results).toEqual([true, true])
    expect(h.created).toHaveLength(2)
    expect(h.appended).toHaveLength(2)
    expect(h.removed).toHaveLength(2) // kein Leak unter Parallelität
    expect(h.created.map((t) => t.value).sort()).toEqual(['A', 'B'])
  })
})
