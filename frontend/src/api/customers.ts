import { api } from './client'
import type { Customer, CustomerCreate, CustomerUpdate, PaginatedResponse } from '../types'

export async function getCustomers(params?: {
  page?: number
  page_size?: number
  search?: string
}): Promise<PaginatedResponse<Customer>> {
  const response = await api.get('/customers', { params })
  return response.data
}

export async function getCustomer(id: string): Promise<Customer> {
  const response = await api.get(`/customers/${id}`)
  return response.data
}

export async function createCustomer(data: CustomerCreate): Promise<Customer> {
  const response = await api.post('/customers', data)
  return response.data
}

export async function updateCustomer(id: string, data: CustomerUpdate): Promise<Customer> {
  const response = await api.put(`/customers/${id}`, data)
  return response.data
}

export async function deleteCustomer(id: string): Promise<void> {
  await api.delete(`/customers/${id}`)
}
