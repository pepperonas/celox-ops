import { getTodos } from '../../api/todos'
import { canDelete } from '../../utils/permissions'
import { useAuthStore } from '../../store/authStore'
import Select from '../../components/Select'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import toast from 'react-hot-toast'
import LoadingIndicator from '../../components/LoadingIndicator'
import TodoList from '../../components/TodoList'
import DeleteDialog from '../../components/DeleteDialog'
import {
  getRainmakerLead,
  deleteRainmakerLead,
  getLeadActivities,
  createLeadActivity,
  deleteActivity,
  getRainmakerTemplates,
  verifyLeadEmail,
  updateRainmakerLead,
} from '../../api/rainmaker'
import { analyzeWebsite, type AnalyzeResult } from '../../api/leads'
import { emailStatusInfo } from './emailStatus'
import { toastWithUndo } from '../../utils/undoToast'
import type { RainmakerTemplate, Todo } from '../../types'
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
  const [verifyingEmail, setVerifyingEmail] = useState(false)
  const [activities, setActivities] = useState<RainmakerActivity[]>([])
  const [templates, setTemplates] = useState<RainmakerTemplate[]>([])
  const [showDelete, setShowDelete] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [completing, setCompleting] = useState<RainmakerActivity | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null)
  const [nextTodo, setNextTodo] = useState<Todo | null>(null)
  const mayDelete = canDelete(useAuthStore((st) => st.role))

  const togglePin = async () => {
    if (!lead) return
    const next = !lead.pinned
    setLead({ ...lead, pinned: next })
    try {
      await updateRainmakerLead(lead.id, { pinned: next })
    } catch {
      toast.error('Konnte den Pin nicht ändern.')
      setLead({ ...lead, pinned: !next })
    }
  }

  const handleAnalyze = async () => {
    if (!lead?.website) return
    setAnalyzing(true)
    setAnalysis(null)
    try {
      setAnalysis(await analyzeWebsite(lead.website))
    } catch {
      toast.error('Website konnte nicht geprüft werden.')
    }
    setAnalyzing(false)
  }

  const load = useCallback(async () => {
    if (!id) return
    try {
      const [l, acts, todos] = await Promise.all([
        getRainmakerLead(id), getLeadActivities(id),
        getTodos({ lead_id: id, status: 'offen', page_size: 50 }).then((r) => r.items).catch(() => []),
      ])
      setLead(l)
      setActivities(acts)
      // Frühestes offenes To-do (nach Fälligkeit, ohne Datum ans Ende) — zählt
      // als geplanter nächster Schritt, wenn keine Rainmaker-Aktion existiert.
      const sorted = [...todos].sort((a, b) => (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999'))
      setNextTodo(sorted[0] ?? null)
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

  // LinkedIn hat keine öffentliche Messaging-API (Partner-only) und verbietet
  // Automatisierung — der konforme Weg: Vorlage in die Zwischenablage, Profil
  // öffnen, dort einfügen und senden.
  const linkedInUrl = lead?.website && lead.website.includes('linkedin.com')
    ? (lead.website.startsWith('http') ? lead.website : `https://${lead.website}`)
    : null

  const useLinkedInTemplate = async (tplId: string) => {
    const tpl = templates.find((t) => t.id === tplId)
    if (!tpl || !linkedInUrl) return
    const text = applyPlaceholders(tpl.body)
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Vorlage kopiert — auf LinkedIn einfügen und senden.')
    } catch {
      toast.error('Kopieren fehlgeschlagen.')
    }
    window.open(linkedInUrl, '_blank', 'noopener')
  }

  const handleVerifyEmail = async () => {
    if (!lead?.email) return
    setVerifyingEmail(true)
    try {
      const updated = await verifyLeadEmail(lead.id)
      setLead(updated)
      const info = emailStatusInfo(updated.email_status)
      toast.success(`E-Mail geprüft: ${info?.label ?? updated.email_status ?? 'unbekannt'}`)
    } catch {
      toast.error('E-Mail-Prüfung fehlgeschlagen.')
    }
    setVerifyingEmail(false)
  }

  const handleDelete = async () => {
    if (!id) return
    try {
      await deleteRainmakerLead(id)
      toast.success('Lead gelöscht.')
      navigate('/pipeline', { back: true })
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

  const emailInfo = emailStatusInfo(lead.email_status)
  const rows: [string, React.ReactNode][] = [
    ['Ansprechpartner', lead.contact_name || '–'],
    ['Funktion', lead.role || '–'],
    ['Geschäftsführung', lead.decision_maker || '–'],
    ['Mitarbeiter', lead.employee_count != null ? lead.employee_count.toLocaleString('de-DE') : '–'],
    ['Telefon', lead.phone || '–'],
    ['E-Mail', lead.email ? (
      <span className="inline-flex items-center gap-2 flex-wrap">
        <span>{lead.email}</span>
        {emailInfo && <span className={`text-xs font-medium ${emailInfo.cls}`} title={emailInfo.title}>{emailInfo.label}</span>}
        <button onClick={handleVerifyEmail} disabled={verifyingEmail}
                className="text-xs text-accent hover:text-accent-hover disabled:opacity-50">
          {verifyingEmail ? 'prüfe…' : 'prüfen'}
        </button>
      </span>
    ) : '–'],
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
          <button onClick={() => navigate('/pipeline', { back: true })} className="md-state grid place-items-center w-10 h-10 rounded-full text-text-muted hover:text-text transition-colors duration-short">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className="text-2xl font-semibold text-text tracking-tight truncate">{lead.company}</h2>
          <span className="shrink-0 text-xs font-medium px-3 py-1 rounded-full" style={{ backgroundColor: color + '26', color }}>{STATUS_LABELS[lead.status]}</span>
          <span className={`shrink-0 text-xs font-medium px-3 py-1 rounded-full ${PRIORITY_TONE[lead.priority]}`}>{PRIORITY_LABELS[lead.priority]}</span>
        </div>
        <div className="flex gap-2 shrink-0 items-center">
          <button
            onClick={togglePin}
            title={lead.pinned ? 'Pin lösen' : 'Anpinnen (oben in der Pipeline-Spalte)'}
            aria-label={lead.pinned ? 'Pin lösen' : 'Anpinnen'}
            className="text-xl leading-none hover:scale-110 transition-transform"
            style={{ color: lead.pinned ? '#e0a500' : 'var(--c-text-muted, #888)' }}
          >
            {lead.pinned ? '★' : '☆'}
          </button>
          {lead.customer_id ? (
            <button onClick={() => navigate(`/kunden/${lead.customer_id}`)} className="btn-secondary">→ Kunde ansehen</button>
          ) : (
            <button onClick={() => navigate(`/kunden/neu?fromLead=${lead.id}`)} className="btn-primary">Als Kunde anlegen</button>
          )}
          <button onClick={() => navigate(`/pipeline/leads/${lead.id}/bearbeiten`)} className="btn-secondary">Bearbeiten</button>
          {mayDelete && <button onClick={() => setShowDelete(true)} className="btn-danger">Löschen</button>}
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
        {lead.website && (
          <button onClick={handleAnalyze} disabled={analyzing} className="btn-secondary !py-2.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            {analyzing ? 'Prüfe…' : 'Website prüfen'}
          </button>
        )}
        {linkedInUrl && (
          <a href={linkedInUrl} target="_blank" rel="noreferrer" className="btn-secondary !py-2.5">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
            LinkedIn
          </a>
        )}
        {linkedInUrl && templates.filter((t) => t.channel === 'message').length > 0 && (
          <Select
            value=""
            onChange={(e) => { if (e.target.value) useLinkedInTemplate(e.target.value) }}
            className="!w-auto"
            compact
            placeholder="LinkedIn-Vorlage…"
            title="LinkedIn-Nachricht aus Vorlage: Text wird kopiert, Profil öffnet sich — dort einfügen"
            options={templates.filter((t) => t.channel === 'message').map((t) => ({ value: t.id, label: t.name }))}
          />
        )}
        {lead.email && templates.filter((t) => t.channel === 'email').length > 0 && (
          <Select
            value=""
            onChange={(e) => { if (e.target.value) useEmailTemplate(e.target.value) }}
            className="!w-auto"
            compact
            placeholder="Vorlage…"
            title="Mail aus Vorlage (Platzhalter ersetzt)"
            options={templates.filter((t) => t.channel === 'email').map((t) => ({ value: t.id, label: t.name }))}
          />
        )}
      </div>

      {/* Website-Analyse (Kaltakquise-Argumente) */}
      {analysis && (
        <div className="rounded-card p-5 mb-6 border border-border bg-surface-container">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-3">
              <span
                className="inline-flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold"
                style={{
                  backgroundColor: (analysis.score >= 80 ? '#22c55e' : analysis.score >= 50 ? '#f59e0b' : '#ef4444') + '26',
                  color: analysis.score >= 80 ? '#22c55e' : analysis.score >= 50 ? '#f59e0b' : '#ef4444',
                }}
              >{analysis.score}</span>
              <div>
                <p className="text-text font-medium">Website-Score</p>
                <p className="text-xs text-text-muted">Ladezeit {(analysis.load_time_ms / 1000).toFixed(1)}s · {analysis.findings.length} Befunde</p>
              </div>
            </div>
            <button onClick={() => setAnalysis(null)} className="text-text-muted hover:text-text text-xs">Schließen</button>
          </div>
          {analysis.findings.length === 0 ? (
            <p className="text-sm text-text-muted">Keine Auffälligkeiten gefunden.</p>
          ) : (
            <ul className="space-y-1.5">
              {analysis.findings.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span
                    className="shrink-0 mt-1.5 w-2 h-2 rounded-full"
                    style={{ backgroundColor: f.severity === 'critical' ? '#ef4444' : f.severity === 'warning' ? '#f59e0b' : '#60a5fa' }}
                  />
                  <span className="text-text-muted"><span className="text-text font-medium">{f.category}:</span> {f.issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Next action */}
      <div className={`rounded-card p-5 mb-6 border ${(nextAction || nextTodo) ? 'bg-surface-container border-border' : isClosed ? 'bg-surface-container border-border' : 'bg-danger/10 border-danger/40'}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-text-muted mb-1">Nächster Schritt</p>
            {nextAction ? (
              <p className="text-text font-medium">
                {ACTIVITY_TYPE_LABELS[nextAction.type]}
                {nextAction.due_date && <span className="text-text-muted font-normal"> · fällig {formatDate(nextAction.due_date)}</span>}
              </p>
            ) : nextTodo ? (
              /* Kein Rainmaker-Schritt, aber ein offenes To-do zählt als geplant. */
              <p className="text-text font-medium">
                ✓ {nextTodo.title}
                {nextTodo.due_date && <span className="text-text-muted font-normal"> · fällig {formatDate(nextTodo.due_date)}</span>}
                <span className="text-text-muted font-normal text-xs"> (To-do)</span>
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
            <div key={label} className="min-w-0">
              <dt className="text-xs text-text-muted mb-0.5">{label}</dt>
              {/* break-words: lange URLs/E-Mails dürfen das Grid nicht sprengen (Mobile) */}
              <dd className="text-sm text-text break-words">{value}</dd>
            </div>
          ))}
        </dl>
        {(lead.target || (lead.tags && lead.tags.length > 0)) && (
          <div className="flex flex-wrap items-center gap-2 mt-5 pt-5 border-t border-border">
            {lead.target && (
              <span
                title="Target — Pitch-Winkel / Pain"
                className="text-xs px-3 py-1 rounded-full bg-accent/15 text-accent font-medium"
              >
                🎯 {lead.target}
              </span>
            )}
            {lead.tags?.map((t) => <span key={t} className="text-xs px-3 py-1 rounded-full bg-surface-high text-text-muted">{t}</span>)}
          </div>
        )}
        {lead.notes && (
          <div className="mt-5 pt-5 border-t border-border">
            <dt className="text-xs text-text-muted mb-1">Notizen</dt>
            <p className="text-sm text-text whitespace-pre-wrap">{lead.notes}</p>
          </div>
        )}
      </div>

      {/* To-dos zum Lead — bewusst getrennt von den Akquise-Aktivitäten:
          keine Punkte, nicht in der Heute-Queue, einfach was zu tun ist. */}
      {id && (
        <div className="bg-surface-container border border-border rounded-card p-6 mb-6">
          <h3 className="text-sm font-semibold text-text mb-4">To-dos</h3>
          <TodoList leadId={id} hideHeading />
        </div>
      )}

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
