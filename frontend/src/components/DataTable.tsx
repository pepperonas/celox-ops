import { useState } from 'react'

export interface Column<T> {
  key: string
  label: string
  render?: (item: T) => React.ReactNode
  sortable?: boolean
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (item: T) => void
  page?: number
  total?: number
  pageSize?: number
  onPageChange?: (page: number) => void
}

export default function DataTable<T extends { id: string }>({
  columns,
  data,
  onRowClick,
  page = 1,
  total = 0,
  pageSize = 20,
  onPageChange,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const totalPages = Math.ceil(total / pageSize)

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sortedData = sortKey
    ? [...data].sort((a, b) => {
        const aVal = (a as Record<string, unknown>)[sortKey]
        const bVal = (b as Record<string, unknown>)[sortKey]
        if (aVal == null) return 1
        if (bVal == null) return -1
        const cmp = String(aVal).localeCompare(String(bVal), 'de')
        return sortDir === 'asc' ? cmp : -cmp
      })
    : data

  return (
    <div className="bg-surface border border-border rounded-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={col.sortable !== false ? () => handleSort(col.key) : undefined}
                  className={`px-3 py-2.5 text-left text-[11px] font-semibold text-text-muted uppercase tracking-wider ${
                    col.sortable !== false ? 'cursor-pointer hover:text-text select-none' : ''
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    {col.label}
                    {sortKey === col.key && (
                      <span className="text-accent">
                        {sortDir === 'asc' ? '\u25B2' : '\u25BC'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-12 text-center text-text-muted text-[13px]"
                >
                  Keine Einträge vorhanden.
                </td>
              </tr>
            ) : (
              sortedData.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onRowClick?.(item)}
                  className={`border-b border-border transition-all duration-150 ${
                    onRowClick
                      ? 'cursor-pointer hover:bg-surface-2'
                      : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-2.5 text-[13px] text-text">
                      {col.render
                        ? col.render(item)
                        : String((item as Record<string, unknown>)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && onPageChange && (
        <div className="flex items-center justify-between px-3 py-2.5 border-t border-border">
          <span className="text-xs text-text-muted">
            {total} Einträge gesamt
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-2.5 py-1 text-xs rounded-[6px] border border-border bg-surface text-text-muted hover:bg-surface-2 hover:text-text disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
            >
              Zurück
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 7) {
                pageNum = i + 1
              } else if (page <= 4) {
                pageNum = i + 1
              } else if (page >= totalPages - 3) {
                pageNum = totalPages - 6 + i
              } else {
                pageNum = page - 3 + i
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  className={`px-2.5 py-1 text-xs rounded-[6px] transition-all duration-150 ${
                    pageNum === page
                      ? 'bg-accent text-white'
                      : 'border border-border bg-surface text-text-muted hover:bg-surface-2 hover:text-text'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-2.5 py-1 text-xs rounded-[6px] border border-border bg-surface text-text-muted hover:bg-surface-2 hover:text-text disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
            >
              Weiter
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
