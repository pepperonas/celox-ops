// Vorschlagskarte: EIN Referenzkunde, den man jetzt ansprechen sollte.
//
// Das ist der Vorschlag, um den es im Marktradar geht — nicht „dieses Produkt ist
// interessant", sondern „diese Firma nutzt X, biete ihr Y an". Deshalb steht auf der
// Karte in dieser Reihenfolge: die Firma, was sie einsetzt, was man ihr anbietet, und
// wie man sie erreicht. Der Score ist eine kleine Zahl am Rand: Er hat die Firma
// hierher gebracht, im Gespräch trägt er nichts bei.
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon'
import type { MarketReferenceGroup } from '../../api/market'

const ORG_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlich',
  konzern: 'Konzern',
  mittelstand: 'Mittelstand',
  unbekannt: 'Typ offen',
}

interface Props {
  k: MarketReferenceGroup
  rang?: number
  onPipeline?: (k: MarketReferenceGroup) => void
  busy?: boolean
}

export default function CustomerSuggestion({ k, rang, onPipeline, busy }: Props) {
  const baustein = k.produkte.find((p) => p.baustein_titel)
  const erreichbar = [
    k.decision_maker && 'Geschäftsführung',
    k.phone && 'Telefon',
    k.email && 'E-Mail',
  ].filter(Boolean) as string[]

  return (
    <div className="card p-4 flex flex-col gap-2 h-full">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Link
            to={`/radar/kunden/${encodeURIComponent(k.company_norm)}`}
            className="text-sm font-semibold text-text hover:text-accent break-words"
          >
            {rang != null && <span className="text-text-muted mr-1.5">{rang}.</span>}
            {k.company}
          </Link>
          <p className="text-[11px] text-text-muted mt-0.5">
            {ORG_LABEL[k.orgtyp] ?? k.orgtyp}
            {k.systeme > 1 && ` · ${k.systeme} Systeme`}
          </p>
        </div>
        <span className="text-xs text-text-muted tabular-nums shrink-0"
              title="Score aus Mehrfachnutzung, passendem Baustein, Umfeld und Ansprechbarkeit — keine Umsatzprognose">
          {k.score}
        </span>
      </div>

      {/* Der Anknüpfungspunkt. */}
      <p className="text-xs text-text-muted">
        <span className="text-text-muted/70">nutzt </span>
        <span className="text-text">{k.produkte[0]?.produkt}</span>
        {k.produkte.length > 1 && (
          <span className="text-text-muted/70"> und {k.produkte.length - 1} weitere</span>
        )}
      </p>

      {/* Das Angebot — der eigentliche Grund für den Anruf. */}
      {baustein ? (
        <p className="text-xs text-accent/90">
          → Baustein {baustein.baustein_nr}: {baustein.baustein_titel}
        </p>
      ) : (
        <p className="text-xs text-text-muted/70">kein Baustein zugeordnet</p>
      )}

      {/* Wie erreichbar? Ohne Kontaktweg beginnt die Ansprache mit Handarbeit —
          das gehört auf die Karte, nicht in eine Überraschung nach dem Klick. */}
      <p className="text-[11px] text-text-muted mt-auto flex items-center gap-1.5">
        {erreichbar.length > 0 ? (
          <>
            {k.decision_maker && <Icon name="user" size={12} className="text-success" />}
            {k.phone && <Icon name="phone" size={12} className="text-success" />}
            {k.email && <Icon name="mail" size={12} className="text-success" />}
            <span>{erreichbar.join(' · ')} bekannt</span>
          </>
        ) : (
          <span>noch kein Kontaktweg — Website und Impressum fehlen</span>
        )}
      </p>

      {onPipeline && k.status !== 'in_pipeline' && (
        <button
          type="button"
          className="btn-secondary text-xs w-full"
          disabled={busy}
          onClick={() => onPipeline(k)}
        >
          in die Pipeline
        </button>
      )}
      {k.status === 'in_pipeline' && (
        <p className="text-[11px] text-success">als Lead übernommen</p>
      )}
    </div>
  )
}
