import { describe, expect, it } from 'vitest'
import { httpHref } from './safeHref'

describe('httpHref', () => {
  it('lässt http und https durch', () => {
    expect(httpHref('https://www.projektron.de')).toBe('https://www.projektron.de/')
    expect(httpHref('http://firma.de/referenzen')).toBe('http://firma.de/referenzen')
  })

  it('blockt javascript: — der eigentliche Zweck', () => {
    // Gemessen: Im heutigen Chromium führt ein solcher href in einem `target="_blank"`-
    // Anker NICHTS aus (Top-Frame-Navigation zu `javascript:` ist geblockt, der Tab
    // bekam Origin `null`). Der Riegel verlässt sich nicht darauf und greift auch dort,
    // wo derselbe Wert nicht in einem Anker landet (`window.open`, `location.assign`).
    expect(httpHref('javascript:alert(1)')).toBeUndefined()
    expect(httpHref('JavaScript:alert(1)')).toBeUndefined()
    expect(httpHref('  javascript:alert(1)  ')).toBeUndefined()
  })

  it('blockt weitere ausführbare und einbettende Schemata', () => {
    for (const u of ['data:text/html,<script>alert(1)</script>', 'vbscript:msgbox(1)',
                     'file:///etc/passwd', 'blob:https://x/y']) {
      expect(httpHref(u), u).toBeUndefined()
    }
  })

  it('blockt erfundene http-ähnliche Schemata', () => {
    // Der Ernter filtert mit `startswith("http")` — „httpx://" käme durch.
    expect(httpHref('httpx://evil.example')).toBeUndefined()
  })

  it('leere und kaputte Werte ergeben undefined, nicht einen toten Link', () => {
    // Ein `<a href="">` lädt die Seite neu — deshalb undefined, damit der Aufrufort
    // den Link gar nicht rendert.
    expect(httpHref(null)).toBeUndefined()
    expect(httpHref(undefined)).toBeUndefined()
    expect(httpHref('')).toBeUndefined()
    expect(httpHref('   ')).toBeUndefined()
    expect(httpHref('kein-url')).toBeUndefined()
    expect(httpHref('/nur/ein/pfad')).toBeUndefined()
  })

  it('mailto und tel gehören NICHT hierher', () => {
    // Sie sind erlaubt, aber über eigene Aufrufe (`mailto:${email}`) — dieser Helfer
    // ist für externe Web-Adressen. Sonst würde er ein `mailto:` durchlassen, wo eine
    // Website erwartet wird.
    expect(httpHref('mailto:a@b.de')).toBeUndefined()
    expect(httpHref('tel:+4930123')).toBeUndefined()
  })
})
