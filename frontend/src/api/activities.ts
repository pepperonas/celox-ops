import { api } from './client'
import type { Activity, ActivityCreate, PaginatedResponse } from '../types'

export async function getActivities(
  customer_id: string,
  page: number = 1,
): Promise<PaginatedResponse<Activity>> {
  const response = await api.get('/activities', { params: { customer_id, page } })
  return response.data
}

export async function createActivity(data: ActivityCreate): Promise<Activity> {
  const response = await api.post('/activities', data)
  return response.data
}

export async function deleteActivity(id: string): Promise<void> {
  await api.delete(`/activities/${id}`)
}
