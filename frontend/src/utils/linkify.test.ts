import { describe, expect, it } from 'vitest'
import { linkifyParts, splitTrailingPunct } from './linkify'

describe('splitTrailingPunct', () => {
  it('trennt nachgestellte Satzzeichen', () => {
    expect(splitTrailingPunct('https://celox.io.')).toEqual(['https://celox.io', '.'])
    expect(splitTrailingPunct('https://x.de),')).toEqual(['https://x.de', '),'])
  })
  it('lässt saubere URLs unverändert', () => {
    expect(splitTrailingPunct('https://celox.io')).toEqual(['https://celox.io', ''])
  })
})

describe('linkifyParts', () => {
  it('erkennt eine URL im Notiztext', () => {
    const parts = linkifyParts('Referenz: https://www.projektron.de/referenzen/show/peak-system-technik/')
    expect(parts[0]).toEqual({ type: 'text', value: 'Referenz: ' })
    expect(parts[1]).toEqual({
      type: 'link', href: 'https://www.projektron.de/referenzen/show/peak-system-technik/', trail: '',
    })
  })

  it('mehrere URLs + Text', () => {
    const parts = linkifyParts('a https://x.de b https://y.de c')
    expect(parts.filter((p) => p.type === 'link')).toHaveLength(2)
    expect(parts.map((p) => (p.type === 'text' ? p.value : `[${p.href}]`)).join('')).toBe(
      'a [https://x.de] b [https://y.de] c',
    )
  })

  it('trennt Satzzeichen als eigenen Textteil', () => {
    const parts = linkifyParts('siehe https://celox.io.')
    const link = parts.find((p) => p.type === 'link')!
    expect(link).toEqual({ type: 'link', href: 'https://celox.io', trail: '.' })
  })

  it('ohne URL ein reiner Textteil', () => {
    expect(linkifyParts('HR: HRB 9183')).toEqual([{ type: 'text', value: 'HR: HRB 9183' }])
  })

  it('leerer Text ergibt keine Teile', () => {
    expect(linkifyParts('')).toEqual([])
  })
})
