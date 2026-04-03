import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import { api } from '../../api/client'
import { getLead, createLead, updateLead, analyzeWebsite, type AnalyzeResult } from '../../api/leads'
import type { LeadCreate } from '../../types'

const statusOptions = [
  { value: 'neu', label: 'Neu' },
  { value: 'kontaktiert', label: 'Kontaktiert' },
  { value: 'interessiert', label: 'Interessiert' },
  { value: 'abgelehnt', label: 'Abgelehnt' },
]

const emptyForm: LeadCreate = {
  url: '',
  name: '',
  company: '',
  email: '',
  phone: '',
  notes: '',
  status: 'neu',
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? '#3fb950' : score >= 40 ? '#d29922' : '#f85149'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-surface-2 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-2xl font-bold tabular-nums" style={{ color }}>{score}%</span>
    </div>
  )
}

function SeverityDot({ severity }: { severity: string }) {
  const color = severity === 'critical' ? '#f85149' : severity === 'warning' ? '#d29922' : '#8b949e'
  return <span className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5" style={{ background: color, display: 'inline-block' }} />
}

export default function LeadForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<LeadCreate>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    if (id) {
      getLead(id).then((l) =>
        setForm({
          url: l.url,
          name: l.name,
          company: l.company,
          email: l.email,
          phone: l.phone,
          notes: l.notes,
          status: l.status,
        }),
      )
    }
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleAnalyze = async () => {
    if (!form.url) return
    setAnalyzing(true)
    setAnalysis(null)
    try {
      const result = await analyzeWebsite(form.url)
      setAnalysis(result)
    } catch {
      toast.error('Analyse fehlgeschlagen.')
    }
    setAnalyzing(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateLead(id!, form)
        toast.success('Lead aktualisiert.')
      } else {
        await createLead(form)
        toast.success('Lead erstellt.')
      }
      navigate('/vorgemerkt')
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  const criticalCount = analysis?.findings.filter(f => f.severity === 'critical').length || 0
  const warningCount = analysis?.findings.filter(f => f.severity === 'warning').length || 0

  return (
    <div className="max-w-4xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Lead bearbeiten' : 'Neue Website vormerken'}
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-[12px] p-6 space-y-5">
          <div>
            <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Website-URL *</label>
            <div className="flex gap-2">
              <input
                type="text"
                name="url"
                value={form.url || ''}
                onChange={handleChange}
                required
                placeholder="https://example.de"
                className="flex-1 !text-base !py-3"
              />
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzing || !form.url}
                className="btn-primary whitespace-nowrap !px-4"
              >
                {analyzing ? 'Prüfe...' : 'Analysieren'}
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!form.url) return
                  toast.loading('PageSpeed läuft...', { id: 'ps' })
                  try {
                    const url = form.url.startsWith('http') ? form.url : `https://${form.url}`
                    const resp = await api.get('/pagespeed/analyze', { params: { url, strategy: 'mobile' }, responseType: 'blob' })
                    const blobUrl = URL.createObjectURL(resp.data)
                    window.open(blobUrl, '_blank')
                    toast.success('PageSpeed Report erstellt.', { id: 'ps' })
                  } catch {
                    toast.error('PageSpeed fehlgeschlagen.', { id: 'ps' })
                  }
                }}
                disabled={!form.url}
                className="btn-secondary whitespace-nowrap !px-4"
              >
                PageSpeed
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Name</label>
              <input type="text" name="name" value={form.name || ''} onChange={handleChange} className="w-full !py-2.5" placeholder="Ansprechpartner" />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Firma</label>
              <input type="text" name="company" value={form.company || ''} onChange={handleChange} className="w-full !py-2.5" placeholder="Firmenname" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">E-Mail</label>
              <input type="email" name="email" value={form.email || ''} onChange={handleChange} className="w-full !py-2.5" placeholder="info@example.de" />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Telefon</label>
              <input type="tel" name="phone" value={form.phone || ''} onChange={handleChange} className="w-full !py-2.5" placeholder="0123 / 456789" />
            </div>
          </div>

          <FormField
            label="Status"
            name="status"
            type="select"
            value={form.status || 'neu'}
            onChange={handleChange}
            options={statusOptions}
          />

          <div>
            <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Notizen</label>
            <textarea
              name="notes"
              value={form.notes || ''}
              onChange={handleChange}
              placeholder="Was ist an der Website verbesserungswürdig, Gesprächsnotizen..."
              rows={5}
              className="w-full !py-3"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => navigate('/vorgemerkt')} className="btn-secondary">
              Abbrechen
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Speichern...' : 'Speichern'}
            </button>
          </div>
        </form>

        {/* Analysis Panel */}
        <div className="space-y-4">
          {analyzing && (
            <div className="bg-surface border border-border rounded-[12px] p-6 text-center">
              <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className="text-text-muted text-sm">Website wird analysiert...</p>
            </div>
          )}

          {analysis && !analyzing && (
            <>
              {/* Score */}
              <div className="bg-surface border border-border rounded-[12px] p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-text uppercase tracking-wider">Website-Qualität</h3>
                  <span className="text-xs text-text-muted">{analysis.load_time_ms}ms Ladezeit</span>
                </div>
                <ScoreBar score={analysis.score} />
                <div className="flex gap-4 mt-3 text-xs">
                  {criticalCount > 0 && <span className="text-danger">{criticalCount} kritisch</span>}
                  {warningCount > 0 && <span className="text-warning">{warningCount} Warnung{warningCount > 1 ? 'en' : ''}</span>}
                  {criticalCount === 0 && warningCount === 0 && <span className="text-success">Keine Probleme gefunden</span>}
                </div>
              </div>

              {/* Findings */}
              <div className="bg-surface border border-border rounded-[12px] p-6">
                <h3 className="text-sm font-semibold text-text uppercase tracking-wider mb-4">Analyse-Ergebnisse</h3>
                <div className="space-y-3">
                  {analysis.findings.map((f, i) => (
                    <div key={i} className="flex gap-2.5">
                      <SeverityDot severity={f.severity} />
                      <div className="flex-1 min-w-0">
                        <span className="text-xs uppercase tracking-wider text-text-muted">{f.category}</span>
                        <p className="text-sm text-text mt-0.5">{f.issue}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Arguments */}
              {(criticalCount > 0 || warningCount > 0) && (
                <div className="bg-surface border border-accent/30 rounded-[12px] p-6">
                  <h3 className="text-sm font-semibold text-accent uppercase tracking-wider mb-3">Gesprächsargumente</h3>
                  <ul className="space-y-2 text-sm text-text">
                    {analysis.findings.filter(f => f.severity !== 'info').map((f, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-accent mt-0.5">-</span>
                        <span>{f.issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {!analysis && !analyzing && (
            <div className="bg-surface border border-border rounded-[12px] p-6 text-center">
              <svg className="w-12 h-12 mx-auto text-text-muted mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <p className="text-text-muted text-sm">URL eingeben und "Analysieren" klicken</p>
              <p className="text-text-muted text-xs mt-1">Prüft SSL, Ladezeit, SEO, Mobile, Sicherheit</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
