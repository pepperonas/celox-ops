import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import { toastWithUndo } from '../../utils/undoToast'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import LoadingIndicator from '../../components/LoadingIndicator'
import PipelineNav from './PipelineNav'
import LinkedInImportModal from './LinkedInImportModal'
import LeadDiscoveryModal from './LeadDiscoveryModal'
import { useAiLeadStore } from '../../store/aiLeadStore'
import { getRainmakerLeads, updateRainmakerLead } from '../../api/rainmaker'
import { formatCurrency } from '../../utils/formatters'
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import { PIPELINE_STATUSES, STATUS_LABELS, STATUS_COLORS, PRIORITY_TONE, PRIORITY_LABELS } from './constants'
import { sourceBadge, sourceKey } from './leadSources'
import { EMAIL_DELIVERABLE, EMAIL_PROBLEM } from './emailStatus'
import PipelineTimeFilter, { DEFAULT_TIME_FILTER, type TimeFilterValue } from './PipelineTimeFilter'
import { presetWindow, detectLastImportWindow, inWindow, toMs } from './timeFilter'

// Generische Auto-Tags, die keine Branche sind → auf der Karte nicht als Branche zeigen.
const GENERIC_TAGS = new Set(['discovery', 'rainmaker', 'linkedin', 'ki-recherche'])
const brancheTag = (tags: string[] | null): string | null =>
  tags?.find((t) => !GENERIC_TAGS.has(t.trim().toLowerCase())) ?? null

const TIME_FILTER_KEY = 'rm-pipeline-timefilter'
const SOURCE_FILTER_KEY = 'rm-pipeline-sourcefilter'
const TARGET_FILTER_KEY = 'rm-pipeline-targetfilter'
const EMAIL_FILTER_KEY = 'rm-pipeline-emailfilter'
function loadTimeFilter(): TimeFilterValue {
  try {
    return { ...DEFAULT_TIME_FILTER, ...JSON.parse(localStorage.getItem(TIME_FILTER_KEY) || '{}') }
  } catch {
    return DEFAULT_TIME_FILTER
  }
}

export default function RainmakerPipeline() {
  const navigate = useAppNavigate()
  const [leads, setLeads] = useState<RainmakerLead[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOver, setDragOver] = useState<RainmakerLeadStatus | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showDiscovery, setShowDiscovery] = useState(false)
  // KI-Lead-Suche lebt global im Store (AiLeadHost rendert Dialog/Pill) → überlebt
  // Dialog-Schließen UND Seitenwechsel. Hier nur: Dialog öffnen + auf Import reagieren.
  const openAi = useAiLeadStore((st) => st.setOpen)
  const aiRunning = useAiLeadStore((st) => st.running)
  const aiOpen = useAiLeadStore((st) => st.open)
  const aiImportedSignal = useAiLeadStore((st) => st.importedSignal)
  const seenAiSignal = useRef(aiImportedSignal)
  // Filter überstehen die Zurück-Navigation (Pipeline remountet) via localStorage.
  const [sourceFilter, setSourceFilter] = useState<string | null>(() => localStorage.getItem(SOURCE_FILTER_KEY) || null)
  const [emailFilter, setEmailFilter] = useState<string | null>(() => localStorage.getItem(EMAIL_FILTER_KEY) || null)
  const [targetFilter, setTargetFilter] = useState<string | null>(() => localStorage.getItem(TARGET_FILTER_KEY) || null)
  const [timeFilter, setTimeFilter] = useState<TimeFilterValue>(loadTimeFilter)

  useEffect(() => {
    if (sourceFilter) localStorage.setItem(SOURCE_FILTER_KEY, sourceFilter)
    else localStorage.removeItem(SOURCE_FILTER_KEY)
  }, [sourceFilter])
  useEffect(() => {
    if (emailFilter) localStorage.setItem(EMAIL_FILTER_KEY, emailFilter)
    else localStorage.removeItem(EMAIL_FILTER_KEY)
  }, [emailFilter])
  useEffect(() => {
    if (targetFilter) localStorage.setItem(TARGET_FILTER_KEY, targetFilter)
    else localStorage.removeItem(TARGET_FILTER_KEY)
  }, [targetFilter])

  const patchTimeFilter = useCallback((patch: Partial<TimeFilterValue>) => {
    setTimeFilter((prev) => {
      const next = { ...prev, ...patch }
      try { localStorage.setItem(TIME_FILTER_KEY, JSON.stringify(next)) } catch { /* ignore */ }
      return next
    })
  }, [])

  const leadTs = useCallback(
    (l: RainmakerLead) => toMs(timeFilter.field === 'created' ? l.created_at : l.updated_at),
    [timeFilter.field],
  )
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

  // Nach einem Import: neu laden und — bei echten Neuanlagen — direkt auf den
  // gerade angelegten Batch filtern (Preset „Letzter Import", Feld = Erstellt).
  const handleImported = useCallback((created: number) => {
    fetchLeads()
    if (created > 0) {
      patchTimeFilter({ preset: 'lastImport', field: 'created' })
      toast('Filter: gerade importierte Leads · „Alle" zum Zurücksetzen', { icon: '✦' })
    }
  }, [fetchLeads, patchTimeFilter])

  // KI-Import erfolgte (im global gehosteten Dialog) → Board neu laden + filtern.
  useEffect(() => {
    if (aiImportedSignal === seenAiSignal.current) return
    seenAiSignal.current = aiImportedSignal
    handleImported(useAiLeadStore.getState().importedCount)
  }, [aiImportedSignal, handleImported])

  // Bookmark umschalten (optimistisch; revert bei Fehler).
  const togglePin = useCallback(async (lead: RainmakerLead) => {
    const next = !lead.pinned
    setLeads((prev) => prev.map((l) => (l.id === lead.id ? { ...l, pinned: next } : l)))
    try {
      await updateRainmakerLead(lead.id, { pinned: next })
    } catch {
      toast.error('Konnte den Pin nicht ändern.')
      setLeads((prev) => prev.map((l) => (l.id === lead.id ? { ...l, pinned: !next } : l)))
    }
  }, [])

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

  // Target-Chips (nach Häufigkeit) — nur Leads mit gesetztem Target.
  const targetChips = useMemo(() => {
    const map = new Map<string, number>()
    for (const l of leads) {
      const t = (l.target || '').trim()
      if (t) map.set(t, (map.get(t) ?? 0) + 1)
    }
    return [...map.entries()].map(([key, count]) => ({ key, count })).sort((a, b) => b.count - a.count)
  }, [leads])

  const timeWindow = useMemo(() => {
    if (timeFilter.preset === 'lastImport') {
      return detectLastImportWindow(leads.map(leadTs), Date.now())
    }
    return presetWindow(timeFilter.preset, Date.now(), timeFilter.from, timeFilter.to)
  }, [timeFilter, leads, leadTs])

  const filteredLeads = useMemo(() => {
    let ls = sourceFilter === null ? leads : leads.filter((l) => sourceKey(l.source) === sourceFilter)
    if (emailFilter === 'deliverable') ls = ls.filter((l) => l.email_status && EMAIL_DELIVERABLE.has(l.email_status))
    else if (emailFilter === 'problem') ls = ls.filter((l) => l.email_status && EMAIL_PROBLEM.has(l.email_status))
    if (targetFilter !== null) ls = ls.filter((l) => (l.target || '').trim() === targetFilter)
    if (timeFilter.preset !== 'all') ls = ls.filter((l) => inWindow(leadTs(l), timeWindow))
    return ls
  }, [leads, sourceFilter, emailFilter, targetFilter, timeFilter.preset, timeWindow, leadTs])

  const emailCounts = useMemo(() => {
    let deliverable = 0, problem = 0
    for (const l of leads) {
      if (l.email_status && EMAIL_DELIVERABLE.has(l.email_status)) deliverable++
      else if (l.email_status && EMAIL_PROBLEM.has(l.email_status)) problem++
    }
    return { deliverable, problem }
  }, [leads])

  // Persistierten Filter zurücksetzen, wenn er ins Leere zeigt (sonst leeres Board
  // ohne Reset-Chip, weil die zugehörige Filterleiste dann ausgeblendet ist).
  useEffect(() => {
    if (leads.length && sourceFilter && !sourceChips.some((c) => c.key === sourceFilter)) {
      setSourceFilter(null)
    }
  }, [leads.length, sourceFilter, sourceChips])
  useEffect(() => {
    if (leads.length && emailFilter && (emailCounts[emailFilter as 'deliverable' | 'problem'] ?? 0) === 0) {
      setEmailFilter(null)
    }
  }, [leads.length, emailFilter, emailCounts])
  useEffect(() => {
    if (leads.length && targetFilter && !targetChips.some((c) => c.key === targetFilter)) {
      setTargetFilter(null)
    }
  }, [leads.length, targetFilter, targetChips])

  if (loading) return <LoadingIndicator />

  return (
    <div>
      <PageHeader
        title="Pipeline"
        subtitle={`${leads.length} Leads`}
        actions={
          <>
            <button onClick={() => openAi(true)} className="btn-primary text-sm">
              ✨ KI-Leads{aiRunning && !aiOpen ? ' · läuft…' : ''}
            </button>
            <button onClick={() => setShowDiscovery(true)} className="btn-secondary text-sm">
              Leads finden
            </button>
            <button onClick={() => setShowImport(true)} className="btn-secondary text-sm">
              LinkedIn-Import
            </button>
          </>
        }
      />
      <PipelineNav />

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

      {/* Target-Filter: eine Chip pro vorkommendem Target + „Alle" (nur wenn Targets gesetzt sind). */}
      {targetChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs text-text-muted mr-1">🎯 Target:</span>
          <button
            onClick={() => setTargetFilter(null)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors duration-short ${
              targetFilter === null ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
            }`}
          >
            Alle ({leads.length})
          </button>
          {targetChips.map(({ key, count }) => (
            <button
              key={key}
              onClick={() => setTargetFilter(key)}
              title={key}
              className={`text-xs px-3 py-1 rounded-full border transition-colors duration-short max-w-[240px] truncate ${
                targetFilter === key ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
              }`}
            >
              {key} ({count})
            </button>
          ))}
        </div>
      )}

      {/* E-Mail-Qualitätsfilter (nur wenn Urteile vorliegen). */}
      {(emailCounts.deliverable > 0 || emailCounts.problem > 0) && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs text-text-muted mr-1">E-Mail:</span>
          {([
            { key: null, label: 'Alle' },
            { key: 'deliverable', label: `✓ Zustellbar (${emailCounts.deliverable})` },
            { key: 'problem', label: `⚠ Problem (${emailCounts.problem})` },
          ] as const).map(({ key, label }) => (
            <button
              key={label}
              onClick={() => setEmailFilter(key)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors duration-short ${
                emailFilter === key ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Zeitfilter: Erstellt/Geändert × Presets/Von–Bis/Letzter Import. */}
      <PipelineTimeFilter
        value={timeFilter}
        onChange={patchTimeFilter}
        matchCount={filteredLeads.length}
        totalCount={leads.length}
      />

      {/* Umbruchfähiges Grid statt horizontalem Scroll: alle Status bleiben
          im Viewport — 6 Spalten auf breiten Screens, sonst 3/2/1 im Umbruch. */}
      <div className="grid gap-4 pb-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {PIPELINE_STATUSES.map((statusKey) => {
          const color = STATUS_COLORS[statusKey]
          // Gepinnte Leads oben (stabile Sortierung erhält die restliche Reihenfolge).
          const colLeads = filteredLeads
            .filter((l) => l.status === statusKey)
            .sort((a, b) => Number(b.pinned) - Number(a.pinned))
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
                {visibleLeads.map((lead) => {
                  const branche = brancheTag(lead.tags)
                  return (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={(e) => { e.dataTransfer.setData('text/plain', lead.id); e.dataTransfer.effectAllowed = 'move'; setDraggingId(lead.id) }}
                    onDragEnd={() => { setDraggingId(null); setDragOver(null) }}
                    onClick={() => navigate(`/pipeline/leads/${lead.id}`)}
                    style={lead.pinned ? { borderColor: '#e0a500' } : undefined}
                    className={`bg-surface-high border border-border rounded-md p-3 cursor-grab active:cursor-grabbing transition-all duration-short hover:border-text-muted hover:shadow-elev-1 ${
                      draggingId === lead.id ? 'opacity-40' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-sm font-medium text-text line-clamp-2">{lead.company}</span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={(e) => { e.stopPropagation(); togglePin(lead) }}
                          title={lead.pinned ? 'Pin lösen' : 'Anpinnen (oben in der Spalte)'}
                          aria-label={lead.pinned ? 'Pin lösen' : 'Anpinnen'}
                          className="leading-none text-sm hover:scale-110 transition-transform"
                          style={{ color: lead.pinned ? '#e0a500' : 'var(--c-text-muted, #888)' }}
                        >
                          {lead.pinned ? '★' : '☆'}
                        </button>
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${PRIORITY_TONE[lead.priority]}`}>
                          {PRIORITY_LABELS[lead.priority]}
                        </span>
                      </div>
                    </div>
                    {lead.contact_name && (
                      <div className="text-xs text-text-muted mb-1.5 truncate">{lead.contact_name}</div>
                    )}
                    {lead.target && (
                      <div className="mb-1.5">
                        <span className="inline-block text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-medium truncate max-w-full"
                              title={`Target: ${lead.target}`}>🎯 {lead.target}</span>
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
                  )
                })}
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

      <Fab onClick={() => navigate('/pipeline/leads/neu')} label="Neuer Lead" />
      {showImport && (
        <LinkedInImportModal
          onClose={() => setShowImport(false)}
          onImported={(created) => { setShowImport(false); handleImported(created) }}
        />
      )}
      {showDiscovery && (
        <LeadDiscoveryModal
          onClose={() => setShowDiscovery(false)}
          onImported={(created) => { setShowDiscovery(false); handleImported(created) }}
        />
      )}
    </div>
  )
}
