import { api } from './client'
import type {
  TimeEntry,
  TimeEntryCreate,
  TimeEntryUpdate,
  TimeEntrySummary,
  PaginatedResponse,
} from '../types'

export async function getTimeEntries(params?: {
  customer_id?: string
  date_from?: string
  date_to?: string
  invoiced?: boolean
  page?: number
  page_size?: number
}): Promise<PaginatedResponse<TimeEntry>> {
  const response = await api.get('/time-entries', { params })
  return response.data
}

export async function createTimeEntry(data: TimeEntryCreate): Promise<TimeEntry> {
  const response = await api.post('/time-entries', data)
  return response.data
}

export async function updateTimeEntry(
  id: string,
  data: TimeEntryUpdate,
): Promise<TimeEntry> {
  const response = await api.put(`/time-entries/${id}`, data)
  return response.data
}

export async function deleteTimeEntry(id: string): Promise<void> {
  await api.delete(`/time-entries/${id}`)
}

export async function getTimeEntrySummary(): Promise<TimeEntrySummary[]> {
  const response = await api.get('/time-entries/summary')
  return response.data
}
