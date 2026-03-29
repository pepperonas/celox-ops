import { useEffect, useState, useRef } from 'react'
import toast from 'react-hot-toast'
import { listAttachments, uploadAttachment, downloadAttachment, deleteAttachment } from '../api/attachments'
import type { Attachment } from '../types'

interface Props {
  customer_id?: string
  order_id?: string
  contract_id?: string
}

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
  })
}

export default function FileAttachments({ customer_id, order_id, contract_id }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadAttachments = () => {
    const params: Record<string, string> = {}
    if (customer_id) params.customer_id = customer_id
    if (order_id) params.order_id = order_id
    if (contract_id) params.contract_id = contract_id
    listAttachments(params).then(setAttachments).catch(() => {})
  }

  useEffect(() => {
    loadAttachments()
  }, [customer_id, order_id, contract_id])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await uploadAttachment(file, { customer_id, order_id, contract_id })
      }
      toast.success(files.length === 1 ? 'Datei hochgeladen.' : `${files.length} Dateien hochgeladen.`)
      loadAttachments()
    } catch {
      toast.error('Fehler beim Hochladen.')
    }
    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
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

  return (
    <div className="bg-surface border border-border rounded-[12px] p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text uppercase tracking-wider">
          Anhänge ({attachments.length})
        </h3>
        <label className={`btn-secondary text-xs cursor-pointer ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
          {uploading ? 'Hochladen...' : 'Datei hochladen'}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      {attachments.length === 0 ? (
        <p className="text-text-muted text-sm">Keine Anhänge vorhanden.</p>
      ) : (
        <div className="space-y-2">
          {attachments.map((a) => (
            <div
              key={a.id}
              className="flex items-center gap-3 py-2 px-3 bg-surface-2 rounded-lg"
            >
              <svg className="w-4 h-4 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text truncate">{a.original_name}</p>
                <p className="text-xs text-text-muted">
                  {formatFileSize(a.size)} — {formatDate(a.created_at)}
                </p>
              </div>
              <button
                onClick={() => handleDownload(a)}
                className="text-text-muted hover:text-accent transition-colors flex-shrink-0"
                title="Herunterladen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                onClick={() => handleDelete(a)}
                className="text-text-muted hover:text-red-500 transition-colors flex-shrink-0"
                title="Löschen"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
