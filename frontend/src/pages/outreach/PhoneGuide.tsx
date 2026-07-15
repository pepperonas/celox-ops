export interface PhoneSection {
  heading: string
  text: string
}

/** Zerlegt einen Telefon-Body an ##-Überschriften in Abschnitte. */
export function parsePhoneSections(body: string): PhoneSection[] {
  const out: PhoneSection[] = []
  let cur: PhoneSection | null = null
  for (const line of body.split('\n')) {
    const m = line.match(/^##\s+(.*)$/)
    if (m) {
      cur = { heading: m[1].trim(), text: '' }
      out.push(cur)
    } else if (cur) {
      cur.text += (cur.text ? '\n' : '') + line
    }
  }
  return out.map((s) => ({ heading: s.heading, text: s.text.trim() })).filter((s) => s.heading)
}

interface Props {
  body: string
  onCopy: (text: string, label: string) => void
}

/** Telefon-Gesprächsleitfaden: jeder Abschnitt einzeln kopierbar + „Alles". */
export default function PhoneGuide({ body, onCopy }: Props) {
  const sections = parsePhoneSections(body)
  if (sections.length === 0) {
    return <pre className="whitespace-pre-wrap text-sm text-text font-sans">{body}</pre>
  }
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => onCopy(body, 'Leitfaden')} className="btn-secondary !text-xs !py-1.5">
          Alles kopieren
        </button>
      </div>
      {sections.map((s, i) => (
        <div key={i} className="rounded-lg border border-border bg-surface-container p-3">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-xs font-semibold text-accent uppercase tracking-wide">{s.heading}</span>
            <button
              onClick={() => onCopy(`${s.heading}\n${s.text}`, s.heading)}
              className="text-xs text-text-muted hover:text-text shrink-0"
              title={`Abschnitt „${s.heading}" kopieren`}
            >
              kopieren
            </button>
          </div>
          <p className="whitespace-pre-wrap text-sm text-text">{s.text}</p>
        </div>
      ))}
    </div>
  )
}
