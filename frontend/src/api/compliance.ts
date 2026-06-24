import { api } from './client'

export interface ComplianceItem {
  template_id: string
  name: string
  category: string
  signed: boolean
  signed_at: string | null
  method: string | null
  attachment_id: string | null
  note: string | null
}

export interface ComplianceCustomer {
  customer_id: string
  name: string
  company: string | null
  total_required: number
  signed_count: number
  missing_count: number
  complete: boolean
  items: ComplianceItem[]
}

export interface RequiredTemplate {
  id: string
  name: string
  category: string
}

export interface ComplianceOverview {
  required_templates: RequiredTemplate[]
  customers: ComplianceCustomer[]
  summary: {
    total_customers: number
    fully_compliant: number
    with_gaps: number
    total_missing: number
  }
}

export async function getComplianceOverview(): Promise<ComplianceOverview> {
  const res = await api.get('/compliance/overview')
  return res.data
}

export async function getCustomerCompliance(customerId: string): Promise<ComplianceCustomer> {
  const res = await api.get(`/compliance/customer/${customerId}`)
  return res.data
}

export async function markCompliance(data: {
  customer_id: string
  template_id: string
  signed: boolean
  signed_at?: string
  note?: string
}): Promise<ComplianceItem> {
  const res = await api.post('/compliance/mark', data)
  return res.data
}

export async function uploadSignedDocument(
  file: File,
  customerId: string,
  templateId: string,
): Promise<ComplianceItem> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('customer_id', customerId)
  formData.append('template_id', templateId)
  const res = await api.post('/compliance/upload', formData, {
    headers: { 'Content-Type': undefined },
  })
  return res.data
}

export async function setTemplateRequired(
  templateId: string,
  required: boolean,
): Promise<RequiredTemplate> {
  const res = await api.put(`/compliance/templates/${templateId}/required`, { required })
  return res.data
}
