import { useEffect, useState, useRef } from 'react'
import toast from 'react-hot-toast'
import { getDocumentTemplates, seedDocumentTemplates, generateDocument, previewDocument, type DocumentTemplate } from '../api/documents'
import { getCustomers } from '../api/customers'
import type { Customer } from '../types'

const categoryColors: Record<string, string> = {
  datenschutz: 'bg-[#58a6ff1a] text-accent border border-[#58a6ff30]',
  dienstleistung: 'bg-[#bc8cff1a] text-purple border border-[#bc8cff30]',
  allgemein: 'bg-surface-2 text-text-muted border border-border',
}

const categoryLabels: Record<string, string> = {
  datenschutz: 'Datenschutz',
  dienstleistung: 'Dienstleistung',
  allgemein: 'Allgemein',
}

export default function Documents() {
  const [templates, setTemplates] = useState<DocumentTemplate[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<DocumentTemplate | null>(null)
  const [selectedCustomerId, setSelectedCustomerId] = useState('')
  const [preview, setPreview] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    Promise.all([
      getDocumentTemplates(),
      getCustomers({ page_size: 1000 }),
    ]).then(([tmpls, custRes]) => {
      setTemplates(tmpls)
      setCustomers(custRes.items)
      if (tmpls.length === 0) {
        seedDocumentTemplates().then(() => {
          getDocumentTemplates().then(setTemplates)
          toast.success('Vorlagen wurden erstellt.')
        })
      }
    }).finally(() => setLoading(false))
  }, [])

  const handleSelectTemplate = (tmpl: DocumentTemplate) => {
    setSelectedTemplate(tmpl)
    setPreview('')
  }

  useEffect(() => {
    if (selectedTemplate && selectedCustomerId) {
      setPreviewLoading(true)
      previewDocument(selectedTemplate.id, selectedCustomerId)
        .then(setPreview)
        .catch(() => setPreview(''))
        .finally(() => setPreviewLoading(false))
    } else {
      setPreview('')
    }
  }, [selectedTemplate, selectedCustomerId])

  // Render preview in sandboxed iframe
  useEffect(() => {
    if (preview && iframeRef.current) {
      const doc = iframeRef.current.contentDocument
      if (doc) {
        doc.open()
        doc.write(preview)
        doc.close()
      }
    }
  }, [preview])

  const handleGenerate = async () => {
    if (!selectedTemplate || !selectedCustomerId) return
    setGenerating(true)
    try {
      await generateDocument(selectedTemplate.id, selectedCustomerId)
      toast.success('PDF wurde heruntergeladen.')
    } catch {
      toast.error('Fehler beim Generieren.')
    }
    setGenerating(false)
  }

  const grouped = templates.reduce<Record<string, DocumentTemplate[]>>((acc, t) => {
    if (!acc[t.category]) acc[t.category] = []
    acc[t.category].push(t)
    return acc
  }, {})

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Vertragsdokumente</h2>
      </div>

      {loading ? (
        <div className="text-text-muted py-12 text-center">Laden...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Template List */}
          <div className="space-y-4">
            {Object.entries(grouped).map(([category, tmpls]) => (
              <div key={category}>
                <p className="text-xs uppercase tracking-wider text-text-muted mb-2">{categoryLabels[category] || category}</p>
                <div className="space-y-1">
                  {tmpls.map((tmpl) => (
                    <button
                      key={tmpl.id}
                      onClick={() => handleSelectTemplate(tmpl)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                        selectedTemplate?.id === tmpl.id
                          ? 'bg-accent/15 border border-accent/40'
                          : 'bg-surface border border-border hover:bg-surface-2'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${categoryColors[category] || categoryColors.allgemein}`}>
                          {categoryLabels[category]?.slice(0, 2).toUpperCase() || '??'}
                        </span>
                        <span className="text-sm text-text truncate">{tmpl.name}</span>
                      </div>
                      {tmpl.description && (
                        <p className="text-[11px] text-text-muted mt-1 truncate ml-8">{tmpl.description}</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Preview + Generate */}
          <div className="lg:col-span-2">
            {selectedTemplate ? (
              <div className="space-y-4">
                <div className="bg-surface border border-border rounded-[12px] p-5">
                  <h3 className="text-sm font-semibold text-text mb-1">{selectedTemplate.name}</h3>
                  <p className="text-xs text-text-muted mb-4">{selectedTemplate.description}</p>
                  <div className="flex gap-3 items-end">
                    <div className="flex-1">
                      <label className="block text-xs uppercase tracking-wider text-text-muted mb-2">Kunde auswählen</label>
                      <select
                        value={selectedCustomerId}
                        onChange={(e) => setSelectedCustomerId(e.target.value)}
                        className="w-full"
                      >
                        <option value="">Kunde wählen...</option>
                        {customers.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.company ? `${c.name} (${c.company})` : c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={handleGenerate}
                      disabled={!selectedCustomerId || generating}
                      className="btn-primary whitespace-nowrap"
                    >
                      {generating ? 'Generiert...' : 'PDF herunterladen'}
                    </button>
                  </div>
                </div>

                {previewLoading && (
                  <div className="text-text-muted py-8 text-center">Vorschau wird geladen...</div>
                )}

                {preview && !previewLoading && (
                  <div className="bg-white rounded-[12px] overflow-hidden border border-border">
                    <iframe
                      ref={iframeRef}
                      title="Dokumentvorschau"
                      className="w-full border-0"
                      style={{ height: '800px' }}
                      sandbox="allow-same-origin"
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-surface border border-border rounded-[12px] p-12 text-center">
                <svg className="w-12 h-12 mx-auto text-text-muted mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-text-muted text-sm">Wähle eine Vorlage aus der Liste</p>
                <p className="text-text-muted text-xs mt-1">10 rechtlich relevante Dokumentvorlagen für IT-Consulting</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
