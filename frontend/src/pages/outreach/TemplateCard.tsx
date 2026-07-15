import { useState } from 'react'
import type { OutreachTemplate } from '../../types'
import { CATEGORY_LABEL, CHANNEL_LABEL } from './constants'

interface Props {
  template: OutreachTemplate
  showChannel?: boolean   // in der Suchansicht (kanalübergreifend)
  onCopy: (t: OutreachTemplate) => void
  onEdit: (t: OutreachTemplate) => void
  onToggleFavorite: (t: OutreachTemplate) => void
  onDelete: (t: OutreachTemplate) => void
}

export default function TemplateCard({ template, showChannel, onCopy, onEdit, onToggleFavorite, onDelete }: Props) {
  const [expanded, setExpanded] = useState(false)
  const t = template
  const preview = t.body.replace(/^##\s+/gm, '').trim()

  return (
    <div className="bg-surface-high border border-border rounded-xl p-4 flex flex-col gap-2 transition-all duration-short hover:border-text-muted hover:shadow-elev-1">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-0.5">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-text-muted">{CATEGORY_LABEL[t.category]}</span>
            {showChannel && <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-text-muted">{CHANNEL_LABEL[t.channel]}</span>}
            {t.usage_count > 0 && <span className="text-[10px] text-text-muted" title="So oft kopiert">↗ {t.usage_count}×</span>}
          </div>
          <h3 className="text-sm font-semibold text-text truncate">{t.title}</h3>
          {t.channel === 'email' && t.subject && (
            <p className="text-xs text-text-muted truncate">Betreff: {t.subject}</p>
          )}
        </div>
        <button
          onClick={() => onToggleFavorite(t)}
          title={t.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}
          aria-label={t.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}
          className="shrink-0 text-lg leading-none hover:scale-110 transition-transform"
          style={{ color: t.is_favorite ? '#e0a500' : 'var(--c-text-muted, #888)' }}
        >
          {t.is_favorite ? '★' : '☆'}
        </button>
      </div>

      <p className={`text-sm text-text-muted whitespace-pre-wrap ${expanded ? '' : 'line-clamp-3'}`}>{preview}</p>
      {preview.length > 160 && (
        <button onClick={() => setExpanded((e) => !e)} className="self-start text-xs text-accent hover:underline">
          {expanded ? 'weniger' : 'mehr anzeigen'}
        </button>
      )}
      {t.notes && <p className="text-[11px] text-text-muted italic border-l-2 border-border pl-2">{t.notes}</p>}

      <div className="flex items-center gap-2 mt-1 pt-2 border-t border-border">
        <button onClick={() => onCopy(t)} className="btn-primary !py-2 flex-1 justify-center">
          Kopieren
        </button>
        <button onClick={() => onEdit(t)} className="btn-secondary !py-2 !px-3" title="Bearbeiten">Bearbeiten</button>
        <button onClick={() => onDelete(t)} className="btn-secondary !py-2 !px-3 !text-danger" title="Löschen">Löschen</button>
      </div>
    </div>
  )
}
