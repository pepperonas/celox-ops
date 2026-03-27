import { api } from './client'
import type { Contract, ContractCreate, ContractUpdate, PaginatedResponse } from '../types'

export async function getContracts(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  typ?: string
}): Promise<PaginatedResponse<Contract>> {
  const response = await api.get('/contracts', { params })
  return response.data
}

export async function getContract(id: number): Promise<Contract> {
  const response = await api.get(`/contracts/${id}`)
  return response.data
}

export async function createContract(data: ContractCreate): Promise<Contract> {
  const response = await api.post('/contracts', data)
  return response.data
}

export async function updateContract(id: number, data: ContractUpdate): Promise<Contract> {
  const response = await api.put(`/contracts/${id}`, data)
  return response.data
}

export async function deleteContract(id: number): Promise<void> {
  await api.delete(`/contracts/${id}`)
}
