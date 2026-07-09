import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import DeleteDialog from '../../components/DeleteDialog'
import {
  getRainmakerLead,
  deleteRainmakerLead,
  getLeadActivities,
  createLeadActivity,
  deleteActivity,
  getRainmakerTemplates,
} from '../../api/rainmaker'
import { toastWithUndo } from '../../utils/undoToast'
import type { RainmakerTemplate } from '../../types'
import { formatCurrency, formatDate } from '../../utils/formatters'
import type { RainmakerLead, RainmakerActivity } from '../../types'
import {
  STATUS_LABELS, STATUS_COLORS, PRIORITY_LABELS, PRIORITY_TONE,
  ACTIVITY_TYPE_LABELS, ACTIVITY_TYPE_ICONS, OUTCOME_LABELS,
} from './constants'
import CompleteActionModal from './CompleteActionModal'
import AddActivityModal from './AddActivityModal'

function mapsHref(address: string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
}

export default function RainmakerLeadDetail() {
  const { id } = useParams()
  const navigate = useAppNavigate()
  const [lead, setLead] = useState<RainmakerLead | null>(null)
  const [activities, setActivities] = useState<RainmakerActivity[]>([])
  const [templates, setTemplates] = useState<RainmakerTemplate[]>([])
  const [showDelete, setShowDelete] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [completing, setCompleting] = useState<RainmakerActivity | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    try {
      const [l, acts] = await Promise.all([getRainmakerLead(id), getLeadActivities(id)])
      setLead(l)
      setActivities(acts)
    } catch {
      toast.error('Lead nicht gefunden.')
    }
  }, [id])

  useEffect(() => { load() }, [load])
  useEffect(() => { getRainmakerTemplates().then(setTemplates).catch(() => {}) }, [])

  const applyPlaceholders = (text: string): string =>
    (text || '')
      .split('{company}').join(lead?.company || '')
      .split('{contact_name}').join(lead?.contact_name || '')
      .split('{role}').join(lead?.role || '')

  const useEmailTemplate = (tplId: string) => {
    const tpl = templates.find((t) => t.id === tplId)
    if (!tpl || !lead?.email) return
    const subject = encodeURIComponent(applyPlaceholders(tpl.subject || ''))
    const body = encodeURIComponent(applyPlaceholders(tpl.body))
    window.location.href = `mailto:${lead.email}?subject=${subject}&body=${body}`
  }

  const handleDelete = async () => {
    if (!id) return
    try {
      await deleteRainmakerLead(id)
      toast.success('Lead gelöscht.')
      navigate('/rainmaker/pipeline', { back: true })
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  const handleDeleteActivity = async (actId: string) => {
    const deleted = activities.find((a) => a.id === actId)
    try {
      await deleteActivity(actId)
      load()
      // Undo nur für geplante Aktionen — erledigte tragen Punkte/Streak und
      // würden per Neuanlage als "geplant" wiederkehren.
      if (deleted && deleted.status === 'planned' && lead) {
        toastWithUndo('Aktion gelöscht.', async () => {
          await createLeadActivity(lead.id, {
            type: deleted.type,
            due_date: deleted.due_date,
            notes: deleted.notes,
            goal_id: deleted.goal_id,
          })
          load()
        })
      }
    } catch {
      toast.error('Konnte nicht gelöscht werden.')
    }
  }

  if (!lead) return <LoadingIndicator />

  const color = STATUS_COLORS[lead.status]
  const planned = activities
    .filter((a) => a.status === 'planned')
    .sort((a, b) => (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999'))
  const nextAction = planned[0] ?? null
  const isClosed = ['won', 'lost', 'dormant'].includes(lead.status)

  const rows: [string, React.ReactNode][] = [
    ['Ansprechpartner', lead.contact_name || '–'],
    ['Funktion', lead.role || '–'],
    ['Telefon', lead.phone || '–'],
    ['E-Mail', lead.email || '–'],
    ['Website', lead.website ? <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`} target="_blank" rel="noreferrer" className="text-accent hover:text-accent-hover">{lead.website.replace(/^https?:\/\//, '')}</a> : '–'],
    ['Quelle', lead.source || '–'],
    ['Geschätzter Wert', lead.value_estimate != null ? formatCurrency(lead.value_estimate) : '–'],
    ['Adresse', lead.address || '–'],
    ['Erstellt', formatDate(lead.created_at)],
  ]

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => navigate('/rainmaker/pipeline', { back: true })} className="md-state grid place-items-center w-10 h-10 rounded-full text-text-muted hover:text-text transition-colors duration-short">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-2xl font-semibold text-text tracking-tight truncate">{lead.company}</h2>
          <span className="shrink-0 text-xs font-medium px-3 py-1 rounded-full" style={{ backgroundColor: color + '26', color }}>{STATUS_LABELS[lead.status]}</span>
          <span className={`shrink-0 text-xs font-medium px-3 py-1 rounded-full ${PRIORITY_TONE[lead.priority]}`}>{PRIORITY_LABELS[lead.priority]}</span>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => navigate(`/rainmaker/leads/${lead.id}/bearbeiten`)} className="btn-secondary">Bearbeiten</button>
          <button onClick={() => setShowDelete(true)} className="btn-danger">Löschen</button>
        </div>
      </div>

      {/* Direct-action buttons */}
      <div className="flex flex-wrap gap-2 mb-6">
        {lead.phone && (
          <a href={`tel:${lead.phone}`} className="btn-primary !py-2.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.call} /></svg>
            Anrufen
          </a>
        )}
        {lead.email && (
          <a href={`mailto:${lead.email}`} className="btn-secondary !py-2.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.email} /></svg>
            Mailen
          </a>
        )}
        {lead.address && (
          <a href={mapsHref(lead.address)} target="_blank" rel="noreferrer" className="btn-secondary !py-2.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.visit} /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            Route
          </a>
        )}
        {lead.email && templates.filter((t) => t.channel === 'email').length > 0 && (
          <select
            defaultValue=""
            onChange={(e) => { useEmailTemplate(e.target.value); e.target.value = '' }}
            className="!w-auto !py-2 text-xs"
            title="Mail aus Vorlage (Platzhalter ersetzt)"
          >
            <option value="" disabled>Vorlage…</option>
            {templates.filter((t) => t.channel === 'email').map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Next action */}
      <div className={`rounded-card p-5 mb-6 border ${nextAction ? 'bg-surface-container border-border' : isClosed ? 'bg-surface-container border-border' : 'bg-danger/10 border-danger/40'}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-text-muted mb-1">Nächster Schritt</p>
            {nextAction ? (
              <p className="text-text font-medium">
                {ACTIVITY_TYPE_LABELS[nextAction.type]}
                {nextAction.due_date && <span className="text-text-muted font-normal"> · fällig {formatDate(nextAction.due_date)}</span>}
              </p>
            ) : isClosed ? (
              <p className="text-text-muted text-sm">Lead abgeschlossen — kein nächster Schritt nötig.</p>
            ) : (
              <p className="text-danger font-semibold text-sm">⚠ Kein nächster Schritt — Lead droht zu versanden</p>
            )}
          </div>
          <div className="flex gap-2 shrink-0">
            {nextAction && (
              <button onClick={() => setCompleting(nextAction)} className="btn-primary !py-2">Erledigt</button>
            )}
            <button onClick={() => setShowAdd(true)} className="btn-secondary !py-2">Aktion planen</button>
          </div>
        </div>
      </div>

      {/* Stammdaten */}
      <div className="bg-surface-container border border-border rounded-card p-6 mb-6">
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-text-muted mb-0.5">{label}</dt>
              <dd className="text-sm text-text">{value}</dd>
            </div>
          ))}
        </dl>
        {lead.tags && lead.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-border">
            {lead.tags.map((t) => <span key={t} className="text-xs px-3 py-1 rounded-full bg-surface-high text-text-muted">{t}</span>)}
          </div>
        )}
        {lead.notes && (
          <div className="mt-5 pt-5 border-t border-border">
            <dt className="text-xs text-text-muted mb-1">Notizen</dt>
            <p className="text-sm text-text whitespace-pre-wrap">{lead.notes}</p>
          </div>
        )}
      </div>

      {/* Activity timeline */}
      <div className="bg-surface-container border border-border rounded-card p-6">
        <h3 className="text-sm font-semibold text-text mb-4">Aktivitäten</h3>
        {activities.length === 0 ? (
          <p className="text-text-muted text-sm">Noch keine Aktivitäten — plane den ersten Schritt.</p>
        ) : (
          <div className="space-y-4">
            {activities.map((a) => {
              const done = a.status === 'done'
              return (
                <div key={a.id} className="flex gap-3 group">
                  <div className={`shrink-0 w-9 h-9 rounded-full grid place-items-center ${done ? 'bg-success/15 text-success' : a.status === 'skipped' ? 'bg-surface-high text-text-muted' : 'bg-accent/15 text-accent'}`}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS[a.type]} /></svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-text">{ACTIVITY_TYPE_LABELS[a.type]}</span>
                      {done ? (
                        <span className="text-xs text-success">erledigt {a.completed_at ? formatDate(a.completed_at) : ''}</span>
                      ) : (
                        <span className="text-xs text-text-muted">geplant{a.due_date ? ` · ${formatDate(a.due_date)}` : ''}</span>
                      )}
                      {a.outcome && <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-high text-text-muted">{OUTCOME_LABELS[a.outcome]}</span>}
                      <button onClick={() => handleDeleteActivity(a.id)} className="ml-auto min-w-[32px] min-h-[32px] opacity-100 [@media(hover:hover)]:opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger text-sm transition-opacity" title="Löschen" aria-label="Aktivität löschen">✕</button>
                    </div>
                    {a.notes && <p className="text-sm text-text-muted mt-0.5 whitespace-pre-wrap">{a.notes}</p>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Lead löschen"
        message={`„${lead.company}" und alle zugehörigen Aktivitäten unwiderruflich löschen?`}
      />
      {showAdd && id && (
        <AddActivityModal leadId={id} onClose={() => setShowAdd(false)} onAdded={() => { setShowAdd(false); load() }} />
      )}
      {completing && (
        <CompleteActionModal
          activity={completing}
          leadCompany={lead.company}
          onClose={() => setCompleting(null)}
          onCompleted={() => { setCompleting(null); load() }}
        />
      )}
    </div>
  )
}
