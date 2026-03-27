import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { getInvoices } from '../../api/invoices'
import { formatDate, formatCurrency } from '../../utils/formatters'
import type { Invoice } from '../../types'

const statusOptions = [
  { value: '', label: 'Alle Status' },
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'gestellt', label: 'Gestellt' },
  { value: 'bezahlt', label: 'Bezahlt' },
  { value: 'ueberfaellig', label: 'Überfällig' },
  { value: 'storniert', label: 'Storniert' },
]

export default function InvoiceList() {
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getInvoices({
        page,
        status: statusFilter || undefined,
      })
      setInvoices(res.items)
      setTotal(res.total)
    } catch {
      // handled globally
    }
    setLoading(false)
  }, [page, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns: Column<Invoice>[] = useMemo(
    () => [
      { key: 'invoice_number', label: 'Rechnungsnr.' },
      { key: 'customer_name', label: 'Kunde' },
      { key: 'title', label: 'Titel' },
      {
        key: 'total',
        label: 'Betrag',
        render: (inv) => formatCurrency(inv.total),
      },
      {
        key: 'status',
        label: 'Status',
        render: (inv) => <StatusBadge status={inv.status} />,
      },
      {
        key: 'invoice_date',
        label: 'Datum',
        render: (inv) => formatDate(inv.invoice_date),
      },
    ],
    [],
  )

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Rechnungen</h2>
        <button onClick={() => navigate('/rechnungen/neu')} className="btn-primary">
          Neue Rechnung
        </button>
      </div>

      <div className="flex gap-3 items-center mb-4">
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
      </div>

      {loading ? (
        <div className="text-text-muted py-12 text-center">Laden...</div>
      ) : (
        <DataTable
          columns={columns}
          data={invoices}
          onRowClick={(inv) => navigate(`/rechnungen/${inv.id}`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
