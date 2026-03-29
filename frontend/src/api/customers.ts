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

export async function downloadDsgvoExport(id: string, customerName: string): Promise<void> {
  const res = await api.get(`/customers/${id}/dsgvo-export`, { responseType: 'blob' })
  const safeName = customerName.replace(/[^a-zA-Z0-9äöüÄÖÜß_-]/g, '_')
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `dsgvo-export-${safeName}.json`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
