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
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import { PIPELINE_STATUSES, STATUS_LABELS, STATUS_COLORS } from './constants'
import { sourceBadge, sourceKey } from './leadSources'
import PipelineColumn from './PipelineColumn'
import { PAGE_SIZE, groupByStatus, nextCount } from './pipelineColumns'
import { EMAIL_DELIVERABLE, EMAIL_PROBLEM } from './emailStatus'
import PipelineTimeFilter, { DEFAULT_TIME_FILTER, type TimeFilterValue } from './PipelineTimeFilter'
import Select from '../../components/Select'
import { LEAD_SORT_OPTIONS, sortColumn, type LeadSort } from './leadSort'
import { presetWindow, detectLastImportWindow, inWindow, toMs } from './timeFilter'

const TIME_FILTER_KEY = 'rm-pipeline-timefilter'
const SOURCE_FILTER_KEY = 'rm-pipeline-sourcefilter'
const TARGET_FILTER_KEY = 'rm-pipeline-targetfilter'
const SORT_KEY = 'rm-pipeline-sort'
const EMAIL_FILTER_KEY = 'rm-pipeline-emailfilter'
const FAV_FILTER_KEY = 'rm-pipeline-favfilter'
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
  const [favOnly, setFavOnly] = useState<boolean>(() => localStorage.getItem(FAV_FILTER_KEY) === '1')
  const [sortMode, setSortMode] = useState<LeadSort>(() => (localStorage.getItem(SORT_KEY) as LeadSort) || 'default')
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
  useEffect(() => {
    if (favOnly) localStorage.setItem(FAV_FILTER_KEY, '1')
    else localStorage.removeItem(FAV_FILTER_KEY)
  }, [favOnly])
  useEffect(() => { localStorage.setItem(SORT_KEY, sortMode) }, [sortMode])

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
  // Pro Spalte: wie viele Karten aktuell gerendert werden (wächst beim Scrollen
  // IN der Spalte). Der Deckel hält das DOM klein — Naht für spätere
  // Virtualisierung/serverseitige Pagination.
  const [visibleCounts, setVisibleCounts] = useState<Record<string, number>>({})
  const showMore = useCallback((statusKey: string, total: number) => {
    setVisibleCounts((prev) => ({
      ...prev, [statusKey]: nextCount(prev[statusKey] ?? PAGE_SIZE, total),
    }))
  }, [])
  const showAll = useCallback((statusKey: string, total: number) => {
    setVisibleCounts((prev) => ({ ...prev, [statusKey]: total }))
  }, [])

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

  // Aktuelle Leads als Ref: so bleibt handleDrop stabil (sonst neue Funktion pro
  // Render → memo der Spalten/Karten wirkungslos).
  const leadsRef = useRef(leads)
  useEffect(() => { leadsRef.current = leads }, [leads])

  const handleDrop = useCallback(async (e: React.DragEvent, newStatus: RainmakerLeadStatus) => {
    e.preventDefault()
    setDragOver(null)
    setDraggingId(null)
    const id = e.dataTransfer.getData('text/plain')
    const lead = leadsRef.current.find((l) => l.id === id)
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
  }, [fetchLeads])

  // Stabile Handler für die memoisierten Spalten/Karten.
  const handleDragOverColumn = useCallback((statusKey: RainmakerLeadStatus, e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(statusKey)
  }, [])
  const handleDragLeaveColumn = useCallback(() => setDragOver(null), [])
  const openLead = useCallback((lead: RainmakerLead) => navigate(`/pipeline/leads/${lead.id}`), [navigate])
  const cardDragStart = useCallback((lead: RainmakerLead, e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', lead.id)
    e.dataTransfer.effectAllowed = 'move'
    setDraggingId(lead.id)
  }, [])
  const cardDragEnd = useCallback(() => { setDraggingId(null); setDragOver(null) }, [])

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
    if (favOnly) ls = ls.filter((l) => l.pinned)
    if (timeFilter.preset !== 'all') ls = ls.filter((l) => inWindow(leadTs(l), timeWindow))
    return ls
  }, [leads, sourceFilter, emailFilter, targetFilter, favOnly, timeFilter.preset, timeWindow, leadTs])

  const pinnedCount = useMemo(() => leads.filter((l) => l.pinned).length, [leads])

  // Ein Durchlauf: nach Status gruppieren, dann je Spalte sortieren (gepinnte oben).
  // Hängt NUR an filteredLeads/sortMode — ein Nachladen (visibleCounts) rechnet
  // hier nichts neu.
  const columns = useMemo(() => {
    const grouped = groupByStatus(filteredLeads, PIPELINE_STATUSES)
    const out: Record<string, RainmakerLead[]> = {}
    for (const st of PIPELINE_STATUSES) out[st] = sortColumn(grouped[st], sortMode)
    return out
  }, [filteredLeads, sortMode])

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
  useEffect(() => {
    if (leads.length && favOnly && pinnedCount === 0) setFavOnly(false)
  }, [leads.length, favOnly, pinnedCount])

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

      {/* Favoriten-Filter: ein Toggle-Badge (nur wenn gepinnte Leads existieren). */}
      {pinnedCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs text-text-muted mr-1">Favoriten:</span>
          <button
            onClick={() => setFavOnly((v) => !v)}
            aria-pressed={favOnly}
            title={favOnly ? 'Favoriten-Filter aus' : 'Nur Favoriten anzeigen'}
            className="text-xs px-3 py-1 rounded-full border transition-colors duration-short"
            style={favOnly
              ? { borderColor: '#e0a500', backgroundColor: '#e0a50026', color: 'var(--c-text,#eee)' }
              : { borderColor: 'var(--c-border,#333)', color: 'var(--c-text-muted,#888)' }}
          >
            {favOnly ? '★' : '☆'} Favoriten ({pinnedCount})
          </button>
        </div>
      )}

      {/* Zeitfilter: Erstellt/Geändert × Presets/Von–Bis/Letzter Import. */}
      <PipelineTimeFilter
        value={timeFilter}
        onChange={patchTimeFilter}
        matchCount={filteredLeads.length}
        totalCount={leads.length}
      />

      {/* Sortierung innerhalb jeder Spalte (gepinnte bleiben immer oben). */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-text-muted">Sortieren:</span>
        <Select
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as LeadSort)}
          compact
          aria-label="Sortierung"
          className="!w-auto min-w-[200px]"
          options={LEAD_SORT_OPTIONS}
        />
      </div>

      {/* Umbruchfähiges Grid; jede Spalte scrollt INTERN (Höhe ~70vh gedeckelt) →
          die Seite bleibt kurz und alle Phasen sind erreichbar, auch wenn eine
          Spalte hunderte Leads hat. */}
      <div className="grid gap-4 pb-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {PIPELINE_STATUSES.map((statusKey) => (
          <PipelineColumn
            key={statusKey}
            statusKey={statusKey}
            label={STATUS_LABELS[statusKey]}
            color={STATUS_COLORS[statusKey]}
            leads={columns[statusKey]}
            visible={visibleCounts[statusKey] ?? PAGE_SIZE}
            isOver={dragOver === statusKey}
            draggingId={draggingId}
            sortMode={sortMode}
            onMore={showMore}
            onShowAll={showAll}
            onDragOverColumn={handleDragOverColumn}
            onDragLeaveColumn={handleDragLeaveColumn}
            onDropColumn={handleDrop}
            onOpenLead={openLead}
            onTogglePin={togglePin}
            onCardDragStart={cardDragStart}
            onCardDragEnd={cardDragEnd}
          />
        ))}
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
