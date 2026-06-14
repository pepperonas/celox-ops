import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import LoadingIndicator from '../../components/LoadingIndicator'
import RainmakerNav from './RainmakerNav'
import ProgressHeader from './ProgressHeader'
import RainmakerFooter from './RainmakerFooter'
import CompleteActionModal from './CompleteActionModal'
import { getRainmakerToday } from '../../api/rainmaker'
import { formatCurrency } from '../../utils/formatters'
import type { RainmakerActivity, RainmakerTodayResponse } from '../../types'
import { ACTIVITY_TYPE_LABELS, ACTIVITY_TYPE_ICONS, PRIORITY_TONE, PRIORITY_LABELS } from './constants'

export default function RainmakerToday() {
  const navigate = useNavigate()
  const [data, setData] = useState<RainmakerTodayResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState<{ activity: RainmakerActivity; company: string } | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await getRainmakerToday())
    } catch {
      toast.error('„Heute" konnte nicht geladen werden.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="pb-4">
      <PageHeader title="Rainmaker" subtitle="Was du heute konkret tust" />
      <RainmakerNav />

      {loading || !data ? (
        <LoadingIndicator />
      ) : (
        <>
          <ProgressHeader progress={data.progress} />

          {/* Rotting leads — anti-stalling warning */}
          {data.rotting.length > 0 && (
            <div className="mb-6 rounded-card border-2 border-danger/50 bg-danger/10 overflow-hidden">
              <div className="px-5 py-3 border-b border-danger/30">
                <p className="text-sm font-bold text-danger">
                  ⚠️ {data.rotting.length} Lead{data.rotting.length !== 1 ? 's' : ''} ohne nächsten Schritt
                </p>
                <p className="text-xs text-text-muted mt-0.5">Plane einen Schritt, bevor sie versanden.</p>
              </div>
              <div className="divide-y divide-danger/20">
                {data.rotting.map((l) => (
                  <button key={l.id} onClick={() => navigate(`/rainmaker/leads/${l.id}`)} className="w-full flex items-center gap-3 px-5 py-2.5 hover:bg-danger/5 transition-colors text-left">
                    <span className="text-sm text-text flex-1 truncate">{l.company}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${PRIORITY_TONE[l.priority]}`}>{PRIORITY_LABELS[l.priority]}</span>
                    <span className="text-xs text-danger font-medium">planen →</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Action queue */}
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-text">Heute fällig ({data.queue.length})</h3>
          </div>

          {data.queue.length === 0 ? (
            <div className="card text-center py-16">
              <div className="text-4xl mb-3">🎉</div>
              <p className="text-text font-medium">Alles abgearbeitet</p>
              <p className="text-text-muted text-sm mt-1">Keine fälligen Akquise-Aktionen für heute.</p>
            </div>
          ) : (
            <div className="md-stagger space-y-3">
              {data.queue.map((item) => {
                const { lead, activity, days_overdue } = item
                return (
                  <div key={activity.id} className="card flex items-center gap-4 !py-4 hover:shadow-elev-2 transition-shadow duration-medium">
                    <div className="shrink-0 w-10 h-10 rounded-full bg-accent/15 text-accent grid place-items-center">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS[activity.type]} /></svg>
                    </div>
                    <button onClick={() => navigate(`/rainmaker/leads/${lead.id}`)} className="flex-1 min-w-0 text-left">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-text truncate">{lead.company}</span>
                        {days_overdue > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-danger/15 text-danger font-semibold">{days_overdue}T überfällig</span>}
                      </div>
                      <div className="text-xs text-text-muted truncate">
                        {ACTIVITY_TYPE_LABELS[activity.type]}
                        {lead.contact_name ? ` · ${lead.contact_name}` : ''}
                        {lead.value_estimate ? ` · ${formatCurrency(lead.value_estimate)}` : ''}
                      </div>
                    </button>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {lead.phone && (
                        <a href={`tel:${lead.phone}`} title="Anrufen" className="md-state grid place-items-center w-9 h-9 rounded-full text-accent hover:text-accent-hover transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.call} /></svg>
                        </a>
                      )}
                      {lead.email && (
                        <a href={`mailto:${lead.email}`} title="Mailen" className="md-state grid place-items-center w-9 h-9 rounded-full text-accent hover:text-accent-hover transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.email} /></svg>
                        </a>
                      )}
                      {lead.address && (
                        <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lead.address)}`} target="_blank" rel="noreferrer" title="Route" className="md-state grid place-items-center w-9 h-9 rounded-full text-accent hover:text-accent-hover transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={ACTIVITY_TYPE_ICONS.visit} /></svg>
                        </a>
                      )}
                      <button onClick={() => setCompleting({ activity, company: lead.company })} className="btn-primary !py-2 !px-4 ml-1">Erledigt</button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {completing && (
        <CompleteActionModal
          activity={completing.activity}
          leadCompany={completing.company}
          onClose={() => setCompleting(null)}
          onCompleted={() => { setCompleting(null); load() }}
        />
      )}

      {!loading && <RainmakerFooter />}
    </div>
  )
}
