import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import { toastWithUndo } from '../../utils/undoToast'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import LoadingIndicator from '../../components/LoadingIndicator'
import RainmakerNav from './RainmakerNav'
import RainmakerFooter from './RainmakerFooter'
import LinkedInImportModal from './LinkedInImportModal'
import LeadDiscoveryModal from './LeadDiscoveryModal'
import { getRainmakerLeads, updateRainmakerLead } from '../../api/rainmaker'
import { formatCurrency } from '../../utils/formatters'
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import { PIPELINE_STATUSES, STATUS_LABELS, STATUS_COLORS, PRIORITY_TONE, PRIORITY_LABELS } from './constants'
import { sourceBadge, sourceKey } from './leadSources'

export default function RainmakerPipeline() {
  const navigate = useAppNavigate()
  const [leads, setLeads] = useState<RainmakerLead[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOver, setDragOver] = useState<RainmakerLeadStatus | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showDiscovery, setShowDiscovery] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string | null>(null)  // null = alle
  // Render-Cap pro Spalte (Performance bei tausenden Karten); "mehr anzeigen" hebt auf
  const [expandedCols, setExpandedCols] = useState<Set<string>>(new Set())

  const fetchLeads = useCallback(async () => {
    try {
      // ALLE Seiten laden — die API cappt page_size bei 1000; mit nur der
      // ersten Seite zeigte das Board bei >1000 Leads falsche Spalten/Zähler.
      const all: RainmakerLead[] = []
      let page = 1
      for (;;) {
        const res = await getRainmakerLeads({ page, page_size: 1000 })
        all.push(...res.items)
        if (page >= res.pages || res.items.length === 0) break
        page++
      }
      setLeads(all)
    } catch {
      toast.error('Fehler beim Laden der Leads.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchLeads()
  }, [fetchLeads])

  const handleDrop = async (e: React.DragEvent, newStatus: RainmakerLeadStatus) => {
    e.preventDefault()
    setDragOver(null)
    setDraggingId(null)
    const id = e.dataTransfer.getData('text/plain')
    const lead = leads.find((l) => l.id === id)
    if (!lead || lead.status === newStatus) return

    const prevStatus = lead.status
    setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status: newStatus } : l)))
    try {
      await updateRainmakerLead(id, { status: newStatus })
      toastWithUndo(`„${lead.company}" → ${STATUS_LABELS[newStatus]}`, async () => {
        await updateRainmakerLead(id, { status: prevStatus })
        setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status: prevStatus } : l)))
      })
    } catch {
      toast.error('Fehler beim Verschieben.')
      fetchLeads()
    }
  }

  // Quellen-Chips (nach Häufigkeit) + aktuell gefilterte Leads.
  const sourceChips = useMemo(() => {
    const map = new Map<string, { key: string; count: number; color: string }>()
    for (const l of leads) {
      const key = sourceKey(l.source)
      const entry = map.get(key)
      if (entry) entry.count++
      else map.set(key, { key, count: 1, color: sourceBadge(l.source).color })
    }
    return [...map.values()].sort((a, b) => b.count - a.count)
  }, [leads])

  const filteredLeads = useMemo(
    () => (sourceFilter === null ? leads : leads.filter((l) => sourceKey(l.source) === sourceFilter)),
    [leads, sourceFilter],
  )

  if (loading) return <LoadingIndicator />

  return (
    <div>
      <PageHeader
        title="Pipeline"
        subtitle={`${leads.length} Leads`}
        actions={
          <>
            <button onClick={() => setShowDiscovery(true)} className="btn-primary text-sm">
              Leads finden
            </button>
            <button onClick={() => setShowImport(true)} className="btn-secondary text-sm">
              LinkedIn-Import
            </button>
          </>
        }
      />
      <RainmakerNav />

      {/* Quellen-Filter: eine Chip pro vorkommender Quelle + „Alle". */}
      {sourceChips.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs text-text-muted mr-1">Quelle:</span>
          <button
            onClick={() => setSourceFilter(null)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors duration-short ${
              sourceFilter === null ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
            }`}
          >
            Alle ({leads.length})
          </button>
          {sourceChips.map(({ key, count, color }) => (
            <button
              key={key}
              onClick={() => setSourceFilter(key)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors duration-short ${
                sourceFilter === key ? 'text-text' : 'text-text-muted hover:text-text'
              }`}
              style={sourceFilter === key
                ? { borderColor: color, backgroundColor: color + '26' }
                : { borderColor: 'var(--c-border,#333)' }}
            >
              {key} ({count})
            </button>
          ))}
        </div>
      )}

      {/* Umbruchfähiges Grid statt horizontalem Scroll: alle Status bleiben
          im Viewport — 6 Spalten auf breiten Screens, sonst 3/2/1 im Umbruch. */}
      <div className="grid gap-4 pb-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {PIPELINE_STATUSES.map((statusKey) => {
          const color = STATUS_COLORS[statusKey]
          const colLeads = filteredLeads.filter((l) => l.status === statusKey)
          const isOver = dragOver === statusKey
          const expanded = expandedCols.has(statusKey)
          const visibleLeads = expanded ? colLeads : colLeads.slice(0, 100)
          const hiddenCount = colLeads.length - visibleLeads.length
          return (
            <div
              key={statusKey}
              className="min-w-0 flex flex-col"
              onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOver(statusKey) }}
              onDragLeave={() => setDragOver(null)}
              onDrop={(e) => handleDrop(e, statusKey)}
            >
              <div
                className="rounded-t-lg px-4 py-2.5 flex items-center justify-between"
                style={{ backgroundColor: color + '20', borderTop: `3px solid ${color}` }}
              >
                <span className="text-sm font-semibold" style={{ color }}>{STATUS_LABELS[statusKey]}</span>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: color + '25', color }}>
                  {colLeads.length}
                </span>
              </div>

              <div
                className={`flex-1 min-h-[140px] bg-surface-container border border-border rounded-b-lg p-3 space-y-3 transition-all duration-short ${
                  isOver ? 'border-accent border-dashed bg-accent/5' : ''
                }`}
              >
                {colLeads.length === 0 && (
                  <div className="text-center text-text-muted text-xs py-8">Keine Leads</div>
                )}
                {visibleLeads.map((lead) => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={(e) => { e.dataTransfer.setData('text/plain', lead.id); e.dataTransfer.effectAllowed = 'move'; setDraggingId(lead.id) }}
                    onDragEnd={() => { setDraggingId(null); setDragOver(null) }}
                    onClick={() => navigate(`/rainmaker/leads/${lead.id}`)}
                    className={`bg-surface-high border border-border rounded-md p-3 cursor-grab active:cursor-grabbing transition-all duration-short hover:border-text-muted hover:shadow-elev-1 ${
                      draggingId === lead.id ? 'opacity-40' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-sm font-medium text-text line-clamp-2">{lead.company}</span>
                      <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full ${PRIORITY_TONE[lead.priority]}`}>
                        {PRIORITY_LABELS[lead.priority]}
                      </span>
                    </div>
                    {lead.contact_name && (
                      <div className="text-xs text-text-muted mb-1.5 truncate">{lead.contact_name}</div>
                    )}
                    <div className="flex items-center justify-between text-xs gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {(() => { const b = sourceBadge(lead.source); return (
                          <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded"
                                style={{ backgroundColor: b.color + '22', color: b.color }}
                                title={`Quelle: ${lead.source || 'Manuell'}`}>{b.label}</span>
                        ) })()}
                        {lead.value_estimate ? (
                          <span className="font-medium tabular-nums truncate" style={{ color }}>{formatCurrency(lead.value_estimate)}</span>
                        ) : null}
                      </div>
                      {lead.needs_next_action && (
                        <span className="shrink-0 text-danger text-[10px] font-semibold">⚠ kein Schritt</span>
                      )}
                    </div>
                  </div>
                ))}
                {hiddenCount > 0 && (
                  <button
                    onClick={() => setExpandedCols((prev) => new Set(prev).add(statusKey))}
                    className="w-full text-xs text-accent hover:underline underline-offset-2 py-2"
                  >
                    +{hiddenCount} weitere anzeigen
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <Fab onClick={() => navigate('/rainmaker/leads/neu')} label="Neuer Lead" />
      {showImport && (
        <LinkedInImportModal
          onClose={() => setShowImport(false)}
          onImported={() => { setShowImport(false); fetchLeads() }}
        />
      )}
      {showDiscovery && (
        <LeadDiscoveryModal
          onClose={() => setShowDiscovery(false)}
          onImported={() => { setShowDiscovery(false); fetchLeads() }}
        />
      )}
      <RainmakerFooter />
    </div>
  )
}
