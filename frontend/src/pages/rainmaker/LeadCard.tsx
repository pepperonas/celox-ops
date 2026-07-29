import { memo } from 'react'
import type { RainmakerLead } from '../../types'
import { formatCurrency } from '../../utils/formatters'
import { PRIORITY_LABELS, PRIORITY_TONE } from './constants'
import { sourceBadge } from './leadSources'
import { cityLabel, type LeadSort } from './leadSort'
import { WebScoreBadge } from './WebsiteAnalysisPanel'
import Icon from '../../components/Icon'

/** Generische Import-/Automatik-Tags sind keine Branche. */
const GENERIC_TAGS = new Set(['discovery', 'rainmaker', 'linkedin', 'ki-recherche'])
function brancheTag(tags: string[] | null): string | null {
  return (tags || []).find((t) => t && !GENERIC_TAGS.has(t.toLowerCase())) || null
}

interface Props {
  lead: RainmakerLead
  /** Spaltenfarbe (für den Betrag). */
  color: string
  sortMode: LeadSort
  dragging: boolean
  onOpen: (lead: RainmakerLead) => void
  onTogglePin: (lead: RainmakerLead) => void
  onDragStart: (lead: RainmakerLead, e: React.DragEvent) => void
  onDragEnd: () => void
}

/**
 * Eine Pipeline-Karte. **Memoisiert**: ohne das re-rendert jede State-Änderung
 * (Nachladen einer Spalte, Pin-Toggle, Filter) sämtliche Karten aller Spalten.
 * Alle Callbacks kommen als stabile Referenzen von der Pipeline und bekommen den
 * Lead als Argument — nur so greift `memo`.
 */
function LeadCardBase({
  lead, color, sortMode, dragging, onOpen, onTogglePin, onDragStart, onDragEnd,
}: Props) {
  const branche = brancheTag(lead.tags)
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(lead, e)}
      onDragEnd={onDragEnd}
      onClick={() => onOpen(lead)}
      style={lead.pinned ? { borderColor: '#e0a500' } : undefined}
      className={`pipeline-card-in bg-surface-high border border-border rounded-md p-3 cursor-grab active:cursor-grabbing transition-all duration-short hover:border-text-muted hover:shadow-elev-1 ${
        dragging ? 'opacity-40' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-sm font-medium text-text line-clamp-2">{lead.company}</span>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onTogglePin(lead) }}
            title={lead.pinned ? 'Pin lösen' : 'Anpinnen (oben in der Spalte)'}
            aria-label={lead.pinned ? 'Pin lösen' : 'Anpinnen'}
            className="leading-none text-sm hover:scale-110 transition-transform"
            style={{ color: lead.pinned ? '#e0a500' : 'var(--c-text-muted, #888)' }}
          >
            <Icon name="star" size={15} filled={lead.pinned} />
          </button>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${PRIORITY_TONE[lead.priority]}`}>
            {PRIORITY_LABELS[lead.priority]}
          </span>
        </div>
      </div>
      {(lead.contact_name || lead.employee_count != null) && (
        <div className="text-xs text-text-muted mb-1.5 flex items-center gap-1.5 min-w-0">
          {lead.contact_name && <span className="truncate">{lead.contact_name}</span>}
          {lead.employee_count != null && (
            <span className="shrink-0 tabular-nums" title={`${lead.employee_count.toLocaleString('de-DE')} Mitarbeiter`}>
              · <Icon name="users" size={13} className="mx-0.5" />{lead.employee_count.toLocaleString('de-DE')}
            </span>
          )}
        </div>
      )}
      {sortMode === 'region' && cityLabel(lead.address) && (
        <div className="text-xs text-text-muted mb-1.5 truncate" title={lead.address ?? undefined}><Icon name="pin" size={16} className="mr-1 -mt-0.5" /> {cityLabel(lead.address)}
        </div>
      )}
      {lead.target && (
        <div className="mb-1.5">
          <span className="inline-block text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-medium truncate max-w-full"
                title={`Target: ${lead.target}`}><Icon name="target" size={16} className="mr-1 -mt-0.5" /> {lead.target}</span>
        </div>
      )}
      {branche && (
        <div className="mb-1.5">
          <span className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-surface-container text-text-muted truncate max-w-full"
                title={`Branche: ${branche}`}>{branche}</span>
        </div>
      )}
      <div className="flex items-center justify-between text-xs gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {(() => { const b = sourceBadge(lead.source); return (
            <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: b.color + '22', color: b.color }}
                  title={`Quelle: ${lead.source || 'Manuell'}`}>
              {b.icon && <Icon name={b.icon} size={11} className="mr-0.5 -mt-0.5" />}{b.label}
            </span>
          ) })()}
          <WebScoreBadge score={lead.web_score} rating={lead.web_rating} hasCritical={lead.web_has_critical}
                         analyzedAt={lead.web_analyzed_at} compact />
          {lead.value_estimate ? (
            <span className="font-medium tabular-nums truncate" style={{ color }}>{formatCurrency(lead.value_estimate)}</span>
          ) : null}
        </div>
        {lead.needs_next_action && (
          <span className="shrink-0 text-danger text-[10px] font-semibold"><Icon name="warning" size={16} className="mr-1 -mt-0.5" /> kein Schritt</span>
        )}
      </div>
    </div>
  )
}

export default memo(LeadCardBase)
