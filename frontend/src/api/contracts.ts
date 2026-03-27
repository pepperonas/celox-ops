import { api } from './client'
import type { Contract, ContractCreate, ContractUpdate, PaginatedResponse } from '../types'

export async function getContracts(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  type?: string
  customer_id?: string
}): Promise<PaginatedResponse<Contract>> {
  const response = await api.get('/contracts', { params })
  return response.data
}

export async function getContract(id: string): Promise<Contract> {
  const response = await api.get(`/contracts/${id}`)
  return response.data
}

export async function createContract(data: ContractCreate): Promise<Contract> {
  const response = await api.post('/contracts', data)
  return response.data
}

export async function updateContract(id: string, data: ContractUpdate): Promise<Contract> {
  const response = await api.put(`/contracts/${id}`, data)
  return response.data
}

export async function deleteContract(id: string): Promise<void> {
  await api.delete(`/contracts/${id}`)
}
