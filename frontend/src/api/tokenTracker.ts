import { api } from './client'

export interface TrackerProject {
  name: string
  messages: number
  sessions: number
  last_activity: string
}

export interface TrackerShare {
  id: string
  project: string
  label: string | null
  created_at: string
  expires_at: string | null
  public_url?: string
}

export async function getTrackerProjects(): Promise<TrackerProject[]> {
  const response = await api.get('/token-tracker/projects')
  return response.data
}

export async function getTrackerShares(): Promise<TrackerShare[]> {
  const response = await api.get('/token-tracker/shares')
  return response.data
}

export async function createTrackerShare(project: string, label?: string): Promise<TrackerShare> {
  const response = await api.post('/token-tracker/shares', { project, label })
  return response.data
}

export async function deleteTrackerShare(id: string): Promise<void> {
  await api.delete(`/token-tracker/shares/${id}`)
}
