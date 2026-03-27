import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { getLeads } from '../../api/leads'
import { formatDate } from '../../utils/formatters'
import type { Lead, LeadStatus } from '../../types'

const statusOptions: { value: string; label: string }[] = [
  { value: '', label: 'Alle' },
  { value: 'neu', label: 'Neu' },
  { value: 'kontaktiert', label: 'Kontaktiert' },
  { value: 'interessiert', label: 'Interessiert' },
  { value: 'abgelehnt', label: 'Abgelehnt' },
]

export default function LeadList() {
  const navigate = useNavigate()
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getLeads({
        page,
        search: search || undefined,
        status: statusFilter || undefined,
      })
      setLeads(res.items)
      setTotal(res.total)
    } catch {
      // error handled globally
    }
    setLoading(false)
  }, [page, search, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns: Column<Lead>[] = useMemo(
    () => [
      {
        key: 'url',
        label: 'URL',
        render: (l) => (
          <a
            href={l.url.startsWith('http') ? l.url : `https://${l.url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:text-accent-hover"
            onClick={(e) => e.stopPropagation()}
          >
            {l.url.replace(/^https?:\/\//, '')}
          </a>
        ),
      },
      { key: 'name', label: 'Name' },
      {
        key: 'status',
        label: 'Status',
        render: (l) => <StatusBadge status={l.status} />,
      },
      {
        key: 'notes',
        label: 'Notiz',
        render: (l) =>
          l.notes ? (
            <span className="text-text-muted" title={l.notes}>
              {l.notes.length > 60 ? l.notes.slice(0, 60) + '...' : l.notes}
            </span>
          ) : null,
      },
      {
        key: 'created_at',
        label: 'Erstellt am',
        render: (l) => formatDate(l.created_at),
      },
    ],
    [],
  )

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Vorgemerkt</h2>
        <button onClick={() => navigate('/vorgemerkt/neu')} className="btn-primary">
          Neue Website
        </button>
      </div>

      <div className="flex gap-3 items-center mb-4">
        <input
          type="text"
          placeholder="Leads suchen..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="input-field max-w-md"
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as LeadStatus | '')
            setPage(1)
          }}
          className="input-field w-auto"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-text-muted py-12 text-center">Laden...</div>
      ) : (
        <DataTable
          columns={columns}
          data={leads}
          onRowClick={(l) => navigate(`/vorgemerkt/${l.id}/bearbeiten`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
