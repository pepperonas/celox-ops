import { api } from './client'
import type { Lead, LeadCreate, LeadUpdate, PaginatedResponse } from '../types'

export async function getLeads(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
}): Promise<PaginatedResponse<Lead>> {
  const response = await api.get('/leads', { params })
  return response.data
}

export async function getLead(id: string): Promise<Lead> {
  const response = await api.get(`/leads/${id}`)
  return response.data
}

export async function createLead(data: LeadCreate): Promise<Lead> {
  const response = await api.post('/leads', data)
  return response.data
}

export async function updateLead(id: string, data: LeadUpdate): Promise<Lead> {
  const response = await api.put(`/leads/${id}`, data)
  return response.data
}

export async function deleteLead(id: string): Promise<void> {
  await api.delete(`/leads/${id}`)
}
