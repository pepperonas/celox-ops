// Kundenname als Link zum Kundendatensatz — für Listen, deren Zeile schon
// woandershin klickt (Rechnungen, Ausgaben, Zeiten).
//
// Zwei Dinge, die hier leicht schiefgehen:
//  1. **Zeilenklick:** die umgebende Tabellenzeile navigiert selbst (z. B. zur
//     Rechnung). Ohne `stopPropagation` würden beide Ziele feuern.
//  2. **Echter Link:** als `<a href>` gerendert, damit Cmd/Ctrl+Klick und
//     Mittelklick den Kunden in einem neuen Tab öffnen und Screenreader ihn als
//     Link ansagen. Der normale Klick läuft über `useAppNavigate`, damit die
//     richtungsbewusste Seiten-Animation greift (siehe utils/transitions).
import { useAppNavigate } from '../utils/transitions'
import { isModifiedClick } from '../utils/linkClick'

interface Props {
  customerId?: string | null
  name?: string | null
  /** Fallback, wenn kein Name vorliegt. */
  placeholder?: string
  className?: string
}

export default function CustomerLink({
  customerId,
  name,
  placeholder = '–',
  className = '',
}: Props) {
  const navigate = useAppNavigate()
  const label = (name || '').trim()

  // Ohne Kunden-ID (oder ohne Namen) bleibt es schlichter Text — ein Link ins
  // Leere wäre schlimmer als kein Link.
  if (!customerId || !label) {
    return <span className={className}>{label || placeholder}</span>
  }

  const href = `/kunden/${customerId}`
  return (
    <a
      href={href}
      title={`${label} öffnen`}
      onClick={(e) => {
        e.stopPropagation()
        if (isModifiedClick(e)) return   // neuer Tab/Fenster: Browser macht das
        e.preventDefault()
        navigate(href)
      }}
      className={`hover:text-accent hover:underline underline-offset-2 decoration-dotted
                  rounded-sm transition-colors duration-short ${className}`}
    >
      {label}
    </a>
  )
}
