import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import FilterChips from '../../components/FilterChips'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getContracts } from '../../api/contracts'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Contract } from '../../types'

const statusOptions = [
  { value: '', label: 'Alle Status' },
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'gekuendigt', label: 'Gekündigt' },
  { value: 'ausgelaufen', label: 'Ausgelaufen' },
]

const typeOptions = [
  { value: '', label: 'Alle Typen' },
  { value: 'hosting', label: 'Hosting' },
  { value: 'wartung', label: 'Wartung' },
  { value: 'support', label: 'Support' },
  { value: 'sonstige', label: 'Sonstige' },
]

export default function ContractList() {
  const navigate = useAppNavigate()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getContracts({
        page,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      })
      setContracts(res.items)
      setTotal(res.total)
    } catch {
      // handled globally
    }
    setLoading(false)
  }, [page, statusFilter, typeFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns: Column<Contract>[] = useMemo(
    () => [
      { key: 'title', label: 'Titel' },
      { key: 'customer_name', label: 'Kunde' },
      {
        key: 'type',
        label: 'Typ',
        render: (c) => <StatusBadge status={c.type} />,
      },
      {
        key: 'monthly_amount',
        label: 'Monatl. Betrag',
        render: (c) => formatCurrency(c.monthly_amount),
      },
      {
        key: 'status',
        label: 'Status',
        render: (c) => <StatusBadge status={c.status} />,
      },
      {
        key: 'end_date',
        label: 'Enddatum',
        render: (c) => formatDate(c.end_date),
      },
    ],
    [],
  )

  return (
    <div>
      <PageHeader title="Verträge" />

      <div className="flex flex-col gap-3 mb-5">
        <FilterChips
          options={statusOptions}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v)
            setPage(1)
          }}
        />
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value)
            setPage(1)
          }}
          className="input-field w-48"
        >
          {typeOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <LoadingIndicator />
      ) : (
        <DataTable
          columns={columns}
          data={contracts}
          onRowClick={(c) => navigate(`/vertraege/${c.id}`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Fab onClick={() => navigate('/vertraege/neu')} label="Neuer Vertrag" />
    </div>
  )
}
