import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import axios from 'axios'
import { getCustomer, createCustomer, updateCustomer } from '../../api/customers'
import { getTrackerProjects, createTrackerShare, type TrackerProject } from '../../api/tokenTracker'
import type { CustomerCreate } from '../../types'

const emptyForm: CustomerCreate = {
  name: '',
  company: '',
  email: '',
  phone: '',
  address: '',
  website: '',
  token_tracker_url: '',
  notes: '',
}

export default function CustomerForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<CustomerCreate>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [projects, setProjects] = useState<TrackerProject[]>([])
  const [showProjectPicker, setShowProjectPicker] = useState(false)
  const [projectSearch, setProjectSearch] = useState('')
  const [linkingProject, setLinkingProject] = useState(false)
  const [urlLabels, setUrlLabels] = useState<Record<string, string>>({})

  useEffect(() => {
    if (id) {
      getCustomer(id).then((c) =>
        setForm({
          name: c.name,
          company: c.company,
          email: c.email,
          phone: c.phone,
          address: c.address,
          website: c.website,
          token_tracker_url: c.token_tracker_url,
          notes: c.notes,
        }),
      )
    }
  }, [id])

  // Fetch labels for linked URLs
  useEffect(() => {
    const urls = (() => {
      const val = form.token_tracker_url
      if (!val) return []
      try { const p = JSON.parse(val); return Array.isArray(p) ? p : [val] } catch { return [val] }
    })()
    urls.forEach(url => {
      if (urlLabels[url]) return
      axios.get(url).then(res => {
        setUrlLabels(prev => ({ ...prev, [url]: res.data?.label || '' }))
      }).catch(() => {})
    })
  }, [form.token_tracker_url])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleOpenProjectPicker = async () => {
    try {
      const p = await getTrackerProjects()
      setProjects(p)
      setShowProjectPicker(true)
    } catch {
      toast.error('Token Tracker nicht erreichbar.')
    }
  }

  // Parse existing URLs from JSON array or single string
  const getLinkedUrls = (): string[] => {
    const val = form.token_tracker_url
    if (!val) return []
    try {
      const parsed = JSON.parse(val)
      return Array.isArray(parsed) ? parsed : [val]
    } catch {
      return [val]
    }
  }

  const setLinkedUrls = (urls: string[]) => {
    if (urls.length === 0) setForm({ ...form, token_tracker_url: '' })
    else if (urls.length === 1) setForm({ ...form, token_tracker_url: urls[0] })
    else setForm({ ...form, token_tracker_url: JSON.stringify(urls) })
  }

  const handleLinkProject = async (project: TrackerProject) => {
    setLinkingProject(true)
    try {
      const label = form.company || form.name || 'Kundenprojekt'
      const share = await createTrackerShare(project.name, `${label} — ${project.name}`)
      if (share.public_url) {
        const current = getLinkedUrls()
        if (!current.includes(share.public_url)) {
          setLinkedUrls([...current, share.public_url])
        }
        toast.success(`Projekt "${project.name}" verknüpft.`)
      }
      setShowProjectPicker(false)
    } catch {
      toast.error('Fehler beim Erstellen des Share-Tokens.')
    }
    setLinkingProject(false)
  }

  const handleRemoveUrl = (url: string) => {
    setLinkedUrls(getLinkedUrls().filter(u => u !== url))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isEdit) {
        await updateCustomer(id!, form)
        toast.success('Kunde aktualisiert.')
        navigate(`/kunden/${id}`)
      } else {
        const created = await createCustomer(form)
        toast.success('Kunde erstellt.')
        navigate(`/kunden/${created.id}`)
      }
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(projectSearch.toLowerCase())
  )

  return (
    <div className="max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">
          {isEdit ? 'Kunde bearbeiten' : 'Neuer Kunde'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-[12px] p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Name" name="name" value={form.name || ''} onChange={handleChange} required />
          <FormField label="Firma" name="company" value={form.company || ''} onChange={handleChange} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="E-Mail" name="email" type="email" value={form.email || ''} onChange={handleChange} />
          <FormField label="Telefon" name="phone" type="tel" value={form.phone || ''} onChange={handleChange} />
        </div>
        <FormField label="Website" name="website" value={form.website || ''} onChange={handleChange} placeholder="https://example.de" />

        {/* Token Tracker */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs uppercase tracking-wider text-text-muted">KI-Nutzung (Token Tracker)</label>
            <button
              type="button"
              onClick={handleOpenProjectPicker}
              className="btn-secondary !text-xs !py-1 !px-3"
            >
              Projekt verknüpfen
            </button>
          </div>
          {getLinkedUrls().length > 0 ? (
            <div className="space-y-1.5">
              {getLinkedUrls().map((url, i) => {
                const label = urlLabels[url]
                return (
                  <div key={i} className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-2">
                    <span className="w-2 h-2 rounded-full bg-success flex-shrink-0"></span>
                    <div className="flex-1 min-w-0">
                      {label && <span className="text-sm text-text block truncate">{label}</span>}
                      <span className="text-[11px] text-text-muted font-mono block truncate">{url.replace(/https?:\/\//, '')}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveUrl(url)}
                      className="text-text-muted hover:text-danger transition-colors p-0.5"
                      title="Verknüpfung entfernen"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-xs text-text-muted">Kein Projekt verknüpft. Klicke "Projekt verknüpfen" um KI-Nutzungsdaten zuzuweisen.</p>
          )}
        </div>

        <FormField label="Adresse" name="address" value={form.address || ''} onChange={handleChange} />
        <FormField label="Notizen" name="notes" type="textarea" value={form.notes || ''} onChange={handleChange} />

        <div className="flex justify-end gap-3 pt-4">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            Abbrechen
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Speichern...' : 'Speichern'}
          </button>
        </div>
      </form>

      {/* Project Picker Modal */}
      {showProjectPicker && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50" onClick={() => setShowProjectPicker(false)}>
          <div className="bg-surface border border-border rounded-[16px] p-6 w-full max-w-lg max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-text mb-1">Projekt verknüpfen</h3>
            <p className="text-text-muted text-sm mb-4">Wähle ein Projekt aus dem Token Tracker aus.</p>
            <input
              type="text"
              placeholder="Projekte filtern..."
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
              className="w-full mb-3"
              autoFocus
            />
            <div className="flex-1 overflow-y-auto space-y-1 min-h-0">
              {filteredProjects.length === 0 ? (
                <p className="text-text-muted text-sm py-4 text-center">Keine Projekte gefunden.</p>
              ) : (
                filteredProjects.map((p) => (
                  <button
                    key={p.name}
                    type="button"
                    onClick={() => handleLinkProject(p)}
                    disabled={linkingProject}
                    className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-surface-2 transition-colors flex justify-between items-center group"
                  >
                    <div>
                      <span className="text-sm text-text group-hover:text-accent transition-colors">{p.name}</span>
                      <span className="text-xs text-text-muted ml-2">{p.messages} Nachrichten</span>
                    </div>
                    <span className="text-xs text-text-muted">{p.sessions} Sessions</span>
                  </button>
                ))
              )}
            </div>
            <div className="flex justify-end pt-4 mt-3 border-t border-border">
              <button type="button" onClick={() => setShowProjectPicker(false)} className="btn-secondary">Abbrechen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
