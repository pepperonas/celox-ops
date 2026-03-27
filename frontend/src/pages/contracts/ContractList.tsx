import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { getContracts } from '../../api/contracts'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Contract } from '../../types'

const statusOptions = [
  { value: '', label: 'Alle Status' },
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'gekuendigt', label: 'Gekuendigt' },
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
  const navigate = useNavigate()
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
        typ: typeFilter || undefined,
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
      { key: 'titel', label: 'Titel' },
      { key: 'customer_name', label: 'Kunde' },
      {
        key: 'typ',
        label: 'Typ',
        render: (c) => <StatusBadge status={c.typ} />,
      },
      {
        key: 'monatlicher_betrag',
        label: 'Monatl. Betrag',
        render: (c) => formatCurrency(c.monatlicher_betrag),
      },
      {
        key: 'status',
        label: 'Status',
        render: (c) => <StatusBadge status={c.status} />,
      },
      {
        key: 'end_datum',
        label: 'Enddatum',
        render: (c) => formatDate(c.end_datum),
      },
    ],
    [],
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-100">Vertraege</h2>
        <button onClick={() => navigate('/vertraege/neu')} className="btn-primary">
          Neuer Vertrag
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          className="input-field w-48"
        >
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
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
        <div className="text-gray-500 py-12 text-center">Laden...</div>
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
    </div>
  )
}
