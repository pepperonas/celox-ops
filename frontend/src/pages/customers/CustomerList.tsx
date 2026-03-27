import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable, { type Column } from '../../components/DataTable'
import { getCustomers } from '../../api/customers'
import { formatDate } from '../../utils/formatters'
import type { Customer } from '../../types'

export default function CustomerList() {
  const navigate = useNavigate()
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
      { key: 'firma', label: 'Firma' },
      { key: 'email', label: 'E-Mail' },
      { key: 'telefon', label: 'Telefon' },
      {
        key: 'created_at',
        label: 'Erstellt am',
        render: (c) => formatDate(c.created_at),
      },
    ],
    [],
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-100">Kunden</h2>
        <button onClick={() => navigate('/kunden/neu')} className="btn-primary">
          Neuer Kunde
        </button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Kunden suchen..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="input-field max-w-md"
        />
      </div>

      {loading ? (
        <div className="text-gray-500 py-12 text-center">Laden...</div>
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
    </div>
  )
}
