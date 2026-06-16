import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import FilterChips from '../../components/FilterChips'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getOrders } from '../../api/orders'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Order } from '../../types'

const statusOptions = [
  { value: '', label: 'Alle Status' },
  { value: 'angebot', label: 'Angebot' },
  { value: 'beauftragt', label: 'Beauftragt' },
  { value: 'in_arbeit', label: 'In Arbeit' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
  { value: 'storniert', label: 'Storniert' },
]

export default function OrderList() {
  const navigate = useAppNavigate()
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getOrders({
        page,
        search: search || undefined,
        status: statusFilter || undefined,
      })
      setOrders(res.items)
      setTotal(res.total)
    } catch {
      // handled globally
    }
    setLoading(false)
  }, [page, search, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns: Column<Order>[] = useMemo(
    () => [
      { key: 'title', label: 'Titel' },
      { key: 'customer_name', label: 'Kunde' },
      {
        key: 'status',
        label: 'Status',
        render: (o) => <StatusBadge status={o.status} />,
      },
      {
        key: 'amount',
        label: 'Betrag',
        render: (o) => formatCurrency(o.amount),
      },
      {
        key: 'start_date',
        label: 'Zeitraum',
        render: (o) =>
          `${formatDate(o.start_date)} - ${formatDate(o.end_date)}`,
      },
    ],
    [],
  )

  return (
    <div>
      <PageHeader title="Aufträge" />

      <div className="flex flex-col gap-3 mb-5">
        <input
          type="text"
          placeholder="Aufträge suchen…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="input-field max-w-md"
        />
        <FilterChips
          options={statusOptions}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v)
            setPage(1)
          }}
        />
      </div>

      {loading ? (
        <LoadingIndicator />
      ) : (
        <DataTable
          columns={columns}
          data={orders}
          onRowClick={(o) => navigate(`/auftraege/${o.id}`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Fab onClick={() => navigate('/auftraege/neu')} label="Neuer Auftrag" />
    </div>
  )
}
