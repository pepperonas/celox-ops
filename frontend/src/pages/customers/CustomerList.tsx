import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import DataTable, { type Column } from '../../components/DataTable'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getCustomers } from '../../api/customers'
import { formatDate } from '../../utils/formatters'
import type { Customer } from '../../types'

export default function CustomerList() {
  const navigate = useAppNavigate()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getCustomers({ page, search: search || undefined })
      setCustomers(res.items)
      setTotal(res.total)
    } catch {
      // error handled globally
    }
    setLoading(false)
  }, [page, search])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns: Column<Customer>[] = useMemo(
    () => [
      { key: 'name', label: 'Name' },
      { key: 'company', label: 'Firma' },
      {
        key: 'website',
        label: 'Website',
        render: (c) => c.website ? (
          <a href={c.website.startsWith('http') ? c.website : `https://${c.website}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-hover" onClick={(e) => e.stopPropagation()}>{c.website.replace(/^https?:\/\//, '')}</a>
        ) : null,
      },
      { key: 'email', label: 'E-Mail' },
      {
        key: 'created_at',
        label: 'Erstellt am',
        render: (c) => formatDate(c.created_at),
      },
      {
        key: 'actions',
        label: 'Aktionen',
        render: (c) => (
          <div className="flex items-center gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => navigate(`/rechnungen/neu?customer_id=${c.id}`)}
              className="md-state text-[10px] text-text-muted hover:text-accent border border-border rounded-full px-3 py-1 transition-colors duration-short"
              title="Neue Rechnung für diesen Kunden"
            >
              + Rechnung
            </button>
            <button
              onClick={() => navigate(`/auftraege/neu?customer_id=${c.id}`)}
              className="md-state text-[10px] text-text-muted hover:text-accent border border-border rounded-full px-3 py-1 transition-colors duration-short"
              title="Neuer Auftrag für diesen Kunden"
            >
              + Auftrag
            </button>
          </div>
        ),
      },
    ],
    [navigate],
  )

  return (
    <div>
      <PageHeader title="Kunden" />

      <div className="flex gap-3 items-center mb-5">
        <input
          type="text"
          placeholder="Kunden suchen…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="input-field max-w-md"
        />
      </div>

      {loading ? (
        <LoadingIndicator />
      ) : (
        <DataTable
          columns={columns}
          data={customers}
          onRowClick={(c) => navigate(`/kunden/${c.id}`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Fab onClick={() => navigate('/kunden/neu')} label="Neuer Kunde" />
    </div>
  )
}
