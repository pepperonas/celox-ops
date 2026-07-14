// Vorschläge für die KI-Lead-Suche — die ideale Zielgruppe (Mittelstand, Berlin,
// die bekannten Branchen; 3× Darmstadt). Werden per Fuzzy-Matching gefiltert.
export const BRIEF_SUGGESTIONS: string[] = [
  '10 mittelständische Hausverwaltungen in Berlin mit E-Mail und Website',
  '10 inhabergeführte Steuerkanzleien in Berlin, keine Großkanzleien',
  '10 mittelständische Anwaltskanzleien in Berlin mit Website und E-Mail',
  '10 IT-Dienstleister und Systemhäuser in Berlin, Mittelstand',
  '10 inhabergeführte Werbe- und Digitalagenturen in Berlin mit E-Mail und Website',
  '10 mittelständische Versicherungsmakler in Berlin mit Website und E-Mail',
  '10 unabhängige Finanzberater in Berlin, keine Konzerne',
  '10 inhabergeführte Immobilienmakler in Berlin mit E-Mail und Website',
  '10 Zahnarztpraxen in Berlin mit eigener Website und E-Mail',
  '10 Arztpraxen mittlerer Größe in Berlin mit Website und E-Mail',
  '10 mittelständische Elektrobetriebe in Berlin mit E-Mail und Website',
  '10 Sanitär- und Heizungsbetriebe in Berlin, inhabergeführt',
  '10 Tischlereien und Schreinereien in Berlin mit Website und E-Mail',
  '10 mittelständische Steuerberater in Berlin-Charlottenburg mit E-Mail und Website',
  '10 Makler und Finanzberater in Berlin mit E-Mail und Website',
  '10 mittelständische Hausverwaltungen für WEG-Verwaltung in Berlin',
  '10 inhabergeführte Marketing-Agenturen in Berlin, keine Großkonzerne',
  '10 mittelständische Steuerkanzleien in Darmstadt mit E-Mail und Website',
  '10 inhabergeführte Hausverwaltungen in Darmstadt mit Website und E-Mail',
  '10 IT-Dienstleister und Agenturen in Darmstadt, Mittelstand',
]

function trigrams(value: string): Set<string> {
  const s = '  ' + value.toLowerCase().replace(/\s+/g, ' ').trim() + ' '
  const out = new Set<string>()
  for (let i = 0; i < s.length - 2; i++) out.add(s.slice(i, i + 3))
  return out
}

function trigramSim(a: string, b: string): number {
  const ta = trigrams(a), tb = trigrams(b)
  if (!ta.size || !tb.size) return 0
  let inter = 0
  ta.forEach((x) => { if (tb.has(x)) inter++ })
  return inter / (ta.size + tb.size - inter)
}

/**
 * Fuzzy-Vorschläge: leere/kurze Eingabe → die Standardliste; sonst nach
 * Token-Treffern (Substring) + Trigramm-Ähnlichkeit (fängt Tippfehler) sortiert.
 */
export function matchBriefs(query: string, limit = 6): string[] {
  const q = (query || '').toLowerCase().trim()
  if (q.length < 2) return BRIEF_SUGGESTIONS.slice(0, limit)
  const tokens = q.split(/\s+/).filter((t) => t.length >= 2)
  const scored = BRIEF_SUGGESTIONS.map((s) => {
    const ls = s.toLowerCase()
    const tokHits = tokens.filter((t) => ls.includes(t)).length
    return { s, score: tokHits * 2 + trigramSim(q, s) }
  }).filter((x) => x.score > 0.12)
  scored.sort((a, b) => b.score - a.score)
  const top = scored.slice(0, limit).map((x) => x.s)
  return top.length ? top : BRIEF_SUGGESTIONS.slice(0, limit)
}
