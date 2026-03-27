import { useState, useCallback } from 'react'
import type { PaginatedResponse } from '../types'

interface CrudApi<T, C, U> {
  getAll: (params?: Record<string, unknown>) => Promise<PaginatedResponse<T>>
  getOne: (id: number) => Promise<T>
  create: (data: C) => Promise<T>
  update: (id: number, data: U) => Promise<T>
  remove: (id: number) => Promise<void>
}

interface CrudState<T> {
  items: T[]
  item: T | null
  loading: boolean
  error: string | null
  total: number
  page: number
  pages: number
}

export function useCrud<T, C, U>(apiFns: CrudApi<T, C, U>) {
  const [state, setState] = useState<CrudState<T>>({
    items: [],
    item: null,
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pages: 1,
  })

  const setLoading = () => setState((s) => ({ ...s, loading: true, error: null }))
  const setError = (error: string) => setState((s) => ({ ...s, loading: false, error }))

  const fetch = useCallback(
    async (params?: Record<string, unknown>) => {
      setLoading()
      try {
        const result = await apiFns.getAll(params)
        setState((s) => ({
          ...s,
          items: result.items,
          total: result.total,
          page: result.page,
          pages: result.pages,
          loading: false,
        }))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten.')
      }
    },
    [apiFns],
  )

  const fetchOne = useCallback(
    async (id: number) => {
      setLoading()
      try {
        const result = await apiFns.getOne(id)
        setState((s) => ({ ...s, item: result, loading: false }))
        return result
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden.')
        return null
      }
    },
    [apiFns],
  )

  const create = useCallback(
    async (data: C) => {
      setLoading()
      try {
        const result = await apiFns.create(data)
        setState((s) => ({ ...s, loading: false }))
        return result
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Erstellen.')
        return null
      }
    },
    [apiFns],
  )

  const update = useCallback(
    async (id: number, data: U) => {
      setLoading()
      try {
        const result = await apiFns.update(id, data)
        setState((s) => ({ ...s, loading: false }))
        return result
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Aktualisieren.')
        return null
      }
    },
    [apiFns],
  )

  const remove = useCallback(
    async (id: number) => {
      setLoading()
      try {
        await apiFns.remove(id)
        setState((s) => ({
          ...s,
          items: s.items.filter((item) => (item as { id: number }).id !== id),
          loading: false,
        }))
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Loeschen.')
        return false
      }
    },
    [apiFns],
  )

  return {
    ...state,
    fetch,
    fetchOne,
    create,
    update,
    remove,
  }
}
