import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import FilterChips from '../../components/FilterChips'
import LoadingIndicator from '../../components/LoadingIndicator'
import { getInvoices, updateInvoiceStatus, downloadPdf, recordPayment } from '../../api/invoices'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
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

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === invoices.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(invoices.map((i) => i.id)))
  }

  const handleQuickStatusChange = async (e: React.MouseEvent, inv: Invoice, newStatus: 'gestellt' | 'bezahlt') => {
    e.stopPropagation()
    try {
      await updateInvoiceStatus(inv.id, newStatus)
      toast.success(newStatus === 'bezahlt' ? `${inv.invoice_number} als bezahlt markiert.` : `${inv.invoice_number} als gestellt markiert.`)
      fetchData()
    } catch {
      toast.error('Statusänderung fehlgeschlagen.')
    }
  }

  const handleBulkMarkPaid = async () => {
    if (!selectedIds.size) return
    if (!confirm(`${selectedIds.size} Rechnung(en) als bezahlt markieren?`)) return
    let success = 0, failed = 0
    for (const id of selectedIds) {
      try {
        const inv = invoices.find((i) => i.id === id)
        if (!inv) continue
        await recordPayment(id, inv.total - (inv.amount_paid || 0))
        success++
      } catch { failed++ }
    }
    toast.success(`${success} bezahlt${failed ? `, ${failed} Fehler` : ''}.`)
    setSelectedIds(new Set())
    fetchData()
  }

  const handleBulkDownloadPdfs = async () => {
    if (!selectedIds.size) return
    let count = 0
    for (const id of selectedIds) {
      const inv = invoices.find((i) => i.id === id)
      if (!inv?.pdf_path) continue
      try {
        const blob = await downloadPdf(id)
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${inv.invoice_number}.pdf`
        a.click()
        URL.revokeObjectURL(url)
        count++
        await new Promise((r) => setTimeout(r, 200))
      } catch { /* skip */ }
    }
    toast.success(`${count} PDF(s) heruntergeladen.`)
  }

  const columns: Column<Invoice>[] = useMemo(
    () => [
      {
        key: 'select',
        label: (
          <input
            type="checkbox"
            checked={invoices.length > 0 && selectedIds.size === invoices.length}
            onChange={toggleSelectAll}
            onClick={(e) => e.stopPropagation()}
            className="cursor-pointer"
          />
        ),
        render: (inv) => (
          <input
            type="checkbox"
            checked={selectedIds.has(inv.id)}
            onChange={() => toggleSelect(inv.id)}
            onClick={(e) => e.stopPropagation()}
            className="cursor-pointer"
          />
        ),
      },
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
        render: (inv) => (
          <div className="flex items-center gap-2">
            <StatusBadge status={inv.status} />
            {inv.status === 'entwurf' && (
              <button
                onClick={(e) => handleQuickStatusChange(e, inv, 'gestellt')}
                className="md-state text-[10px] text-text-muted hover:text-accent border border-border rounded-full px-2.5 py-0.5 transition-colors duration-short"
                title="Als gestellt markieren"
              >
                → Gestellt
              </button>
            )}
            {(inv.status === 'gestellt' || inv.status === 'ueberfaellig') && (
              <button
                onClick={(e) => handleQuickStatusChange(e, inv, 'bezahlt')}
                className="md-state text-[10px] text-text-muted hover:text-success border border-border rounded-full px-2.5 py-0.5 transition-colors duration-short"
                title="Als bezahlt markieren"
              >
                ✓ Bezahlt
              </button>
            )}
          </div>
        ),
      },
      {
        key: 'invoice_date',
        label: 'Datum',
        render: (inv) => formatDate(inv.invoice_date),
      },
    ],
    [selectedIds, invoices.length],
  )

  return (
    <div>
      <PageHeader title="Rechnungen" />

      <div className="flex gap-3 items-center mb-5 flex-wrap">
        <FilterChips
          options={statusOptions}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v)
            setPage(1)
            if (v) setSearchParams({ status: v })
            else setSearchParams({})
          }}
        />
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-text-muted">{selectedIds.size} ausgewählt</span>
            <button onClick={handleBulkMarkPaid} className="btn-secondary text-xs !py-1.5 !px-4">Als bezahlt</button>
            <button onClick={handleBulkDownloadPdfs} className="btn-secondary text-xs !py-1.5 !px-4">PDFs laden</button>
            <button onClick={() => setSelectedIds(new Set())} className="md-state text-text-muted text-xs hover:text-text w-7 h-7 rounded-full">×</button>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingIndicator />
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

      <Fab onClick={() => navigate('/rechnungen/neu')} label="Neue Rechnung" />
    </div>
  )
}
