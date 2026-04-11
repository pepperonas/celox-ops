import { useEffect, useState, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { listAttachments, uploadAttachment, downloadAttachment, deleteAttachment, updateAttachment } from '../api/attachments'
import type { Attachment } from '../types'

interface Props {
  customer_id?: string
  order_id?: string
  contract_id?: string
  onCountChange?: (count: number) => void
}

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function FileAttachments({ customer_id, order_id, contract_id, onCountChange }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ description: '', notes: '' })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  const loadAttachments = useCallback(() => {
    const params: Record<string, string> = {}
    if (customer_id) params.customer_id = customer_id
    if (order_id) params.order_id = order_id
    if (contract_id) params.contract_id = contract_id
    listAttachments(params).then((data) => {
      setAttachments(data)
      onCountChange?.(data.length)
    }).catch(() => {})
  }, [customer_id, order_id, contract_id, onCountChange])

  useEffect(() => {
    loadAttachments()
  }, [loadAttachments])

  const doUpload = async (files: File[]) => {
    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        toast.error(`"${file.name}" ist zu groß (max. 20 MB).`)
        return
      }
    }
    setUploading(true)
    try {
      for (const file of files) {
        await uploadAttachment(file, { customer_id, order_id, contract_id })
      }
      toast.success(files.length === 1 ? 'Datei hochgeladen.' : `${files.length} Dateien hochgeladen.`)
      loadAttachments()
    } catch (err: any) {
      if (err?.response?.status === 413) {
        toast.error('Datei zu groß (max. 20 MB).')
      } else {
        toast.error('Fehler beim Hochladen.')
      }
    }
    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    doUpload(Array.from(files))
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) doUpload(files)
  }

  const handleDownload = async (a: Attachment) => {
    try {
      await downloadAttachment(a.id, a.original_name)
    } catch {
      toast.error('Fehler beim Herunterladen.')
    }
  }

  const handleDelete = async (a: Attachment) => {
    if (!confirm(`"${a.original_name}" wirklich löschen?`)) return
    try {
      await deleteAttachment(a.id)
      toast.success('Datei gelöscht.')
      loadAttachments()
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  const startEdit = (a: Attachment) => {
    setEditingId(a.id)
    setEditForm({ description: a.description || '', notes: a.notes || '' })
  }

  const handleSaveEdit = async (a: Attachment) => {
    try {
      await updateAttachment(a.id, {
        description: editForm.description,
        notes: editForm.notes,
      })
      toast.success('Gespeichert.')
      setEditingId(null)
      loadAttachments()
    } catch {
      toast.error('Fehler beim Speichern.')
    }
  }

  return (
    <div>
      {/* Drop zone */}
      <div
        ref={dropRef}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-[12px] p-8 mb-4 text-center transition-colors ${
          dragOver
            ? 'border-accent bg-accent/10'
            : 'border-border hover:border-text-muted'
        } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <svg className="w-8 h-8 mx-auto mb-3 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-sm text-text-muted mb-2">
          {uploading ? 'Hochladen...' : 'Dateien hierher ziehen oder'}
        </p>
        <label className="btn-primary cursor-pointer text-sm">
          Dateien auswählen
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileInput}
            disabled={uploading}
          />
        </label>
        <p className="text-xs text-text-muted mt-2">Max. 20 MB pro Datei</p>
      </div>

      {/* File list */}
      <div className="overflow-x-auto bg-surface border border-border rounded-[12px]">
        <table className="w-full">
          <thead>
            <tr className="bg-surface-2 border-b border-border">
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Datei</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Beschreibung</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Größe</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wider">Datum</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-text-muted uppercase tracking-wider">Aktionen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {attachments.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-text-muted">Keine Dokumente vorhanden.</td></tr>
            ) : (
              attachments.map((a) => (
                <tr key={a.id} className="hover:bg-surface-2 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                      </svg>
                      <span className="text-sm text-text truncate max-w-[200px]" title={a.original_name}>{a.original_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {editingId === a.id ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          placeholder="Beschreibung..."
                          className="text-sm py-1 px-2 w-full"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveEdit(a)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                        />
                        <textarea
                          value={editForm.notes}
                          onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                          placeholder="Notizen..."
                          className="text-sm py-1 px-2 w-full"
                          rows={2}
                          onKeyDown={(e) => {
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                        />
                        <div className="flex gap-1">
                          <button onClick={() => handleSaveEdit(a)} className="text-accent hover:text-accent-hover text-xs" title="Speichern">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button onClick={() => setEditingId(null)} className="text-text-muted hover:text-text text-xs" title="Abbrechen">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div
                        className="cursor-pointer"
                        onClick={() => startEdit(a)}
                        title="Klicken zum Bearbeiten"
                      >
                        {a.description ? (
                          <p className="text-sm text-text">{a.description}</p>
                        ) : (
                          <p className="text-sm text-text-muted italic">Keine Beschreibung</p>
                        )}
                        {a.notes && (
                          <p className="text-xs text-text-muted mt-0.5 truncate max-w-[250px]" title={a.notes}>{a.notes}</p>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-text-muted whitespace-nowrap">{formatFileSize(a.size)}</td>
                  <td className="px-4 py-3 text-sm text-text-muted whitespace-nowrap">{formatDate(a.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {editingId !== a.id && (
                        <button
                          onClick={() => startEdit(a)}
                          className="text-text-muted hover:text-accent transition-colors"
                          title="Bearbeiten"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      )}
                      <button
                        onClick={() => handleDownload(a)}
                        className="text-accent hover:text-accent-hover transition-colors"
                        title="Herunterladen"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(a)}
                        className="text-text-muted hover:text-red-500 transition-colors"
                        title="Löschen"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
