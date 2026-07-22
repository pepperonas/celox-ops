// Reine URL-Erkennung für Freitext (ohne DOM, damit testbar). Die Komponente
// components/Linkified.tsx rendert daraus die <a>-Tags.

export type LinkifyPart =
  | { type: 'text'; value: string }
  | { type: 'link'; href: string; trail: string }

// http(s)-URL bis zum ersten Whitespace / '<'.
const URL_RE = /(https?:\/\/[^\s<]+)/g

/** Trennt nachgestellte Satzzeichen von einer URL (…celox.io. → celox.io + "."). */
export function splitTrailingPunct(url: string): [string, string] {
  const m = url.match(/[.,;:!?)\]]+$/)
  return m ? [url.slice(0, -m[0].length), m[0]] : [url, '']
}

export function linkifyParts(text: string): LinkifyPart[] {
  const parts: LinkifyPart[] = []
  for (let i = 0, chunks = text.split(URL_RE); i < chunks.length; i++) {
    const chunk = chunks[i]
    if (!chunk) continue
    if (i % 2 === 1) {
      const [href, trail] = splitTrailingPunct(chunk)
      parts.push({ type: 'link', href, trail })
    } else {
      parts.push({ type: 'text', value: chunk })
    }
  }
  return parts
}
