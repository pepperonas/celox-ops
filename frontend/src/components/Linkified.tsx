// Rendert Freitext und macht enthaltene URLs zu anklickbaren Links (neuer Tab,
// hervorgehoben). Zeilenumbrüche bleiben erhalten. Logik in utils/linkify.ts.
import { linkifyParts } from '../utils/linkify'

interface Props {
  text: string
  className?: string
}

export default function Linkified({ text, className = '' }: Props) {
  return (
    <p className={`whitespace-pre-wrap break-words ${className}`}>
      {linkifyParts(text).map((part, i) =>
        part.type === 'link' ? (
          <span key={i}>
            <a
              href={part.href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline decoration-accent/40 hover:decoration-accent break-all"
            >
              {part.href}
            </a>
            {part.trail}
          </span>
        ) : (
          <span key={i}>{part.value}</span>
        ),
      )}
    </p>
  )
}
