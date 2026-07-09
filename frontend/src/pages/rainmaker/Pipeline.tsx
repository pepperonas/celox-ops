import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import LoadingIndicator from '../../components/LoadingIndicator'
import RainmakerNav from './RainmakerNav'
import RainmakerFooter from './RainmakerFooter'
import LinkedInImportModal from './LinkedInImportModal'
import { getRainmakerLeads, updateRainmakerLead } from '../../api/rainmaker'
import { formatCurrency } from '../../utils/formatters'
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import { PIPELINE_STATUSES, STATUS_LABELS, STATUS_COLORS, PRIORITY_TONE, PRIORITY_LABELS } from './constants'

export default function RainmakerPipeline() {
  const navigate = useAppNavigate()
  const [leads, setLeads] = useState<RainmakerLead[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOver, setDragOver] = useState<RainmakerLeadStatus | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [showImport, setShowImport] = useState(false)

  const fetchLeads = useCallback(async () => {
    try {
      const res = await getRainmakerLeads({ page_size: 1000 })
      setLeads(res.items)
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

    setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status: newStatus } : l)))
    try {
      await updateRainmakerLead(id, { status: newStatus })
      toast.success(`„${lead.company}" → ${STATUS_LABELS[newStatus]}`)
    } catch {
      toast.error('Fehler beim Verschieben.')
      fetchLeads()
    }
  }

  if (loading) return <LoadingIndicator />

  return (
    <div>
      <PageHeader
        title="Pipeline"
        subtitle={`${leads.length} Leads`}
        actions={
          <button onClick={() => setShowImport(true)} className="btn-secondary text-sm">
            LinkedIn-Import
          </button>
        }
      />
      <RainmakerNav />

      <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: 'calc(100vh - 260px)' }}>
        {PIPELINE_STATUSES.map((statusKey) => {
          const color = STATUS_COLORS[statusKey]
          const colLeads = leads.filter((l) => l.status === statusKey)
          const isOver = dragOver === statusKey
          return (
            <div
              key={statusKey}
              className="flex-1 min-w-[240px] flex flex-col"
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
                className={`flex-1 bg-surface-container border border-border rounded-b-lg p-3 space-y-3 transition-all duration-short ${
                  isOver ? 'border-accent border-dashed bg-accent/5' : ''
                }`}
              >
                {colLeads.length === 0 && (
                  <div className="text-center text-text-muted text-xs py-8">Keine Leads</div>
                )}
                {colLeads.map((lead) => (
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
                    <div className="flex items-center justify-between text-xs">
                      {lead.value_estimate ? (
                        <span className="font-medium tabular-nums" style={{ color }}>{formatCurrency(lead.value_estimate)}</span>
                      ) : <span className="text-text-muted">&ndash;</span>}
                      {lead.needs_next_action && (
                        <span className="text-danger text-[10px] font-semibold">⚠ kein Schritt</span>
                      )}
                    </div>
                  </div>
                ))}
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
      <RainmakerFooter />
    </div>
  )
}
