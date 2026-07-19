import { api } from './client'
import type { HandoffTargetStatus } from '../utils/handoffStatus'

export type HandoffTarget = 'portal' | 'datenschutz'

export interface AddressPreview {
  street?: string
  postal_code?: string
  city?: string
  country?: string
  raw?: string
}

export interface HandoffStatusResponse {
  email_missing: boolean
  portal: { configured: boolean; status: HandoffTargetStatus | null }
  datenschutz: {
    configured: boolean
    status: HandoffTargetStatus | null
    address_preview: AddressPreview | null
  }
}

export interface HandoffPushRequest {
  target: HandoffTarget
  entitlements?: string[]
  send_onboarding?: boolean
  invite_contact?: boolean
}

export interface HandoffPushResponse {
  ok: boolean
  created: boolean
  target: HandoffTarget
  status: HandoffTargetStatus
  onboarding_sent: boolean
  invitation_sent: boolean
}

export async function getHandoffStatus(customerId: string): Promise<HandoffStatusResponse> {
  const r = await api.get(`/customers/${customerId}/handoff`)
  return r.data
}

export async function pushHandoff(
  customerId: string,
  body: HandoffPushRequest
): Promise<HandoffPushResponse> {
  const r = await api.post(`/customers/${customerId}/handoff`, body)
  return r.data
}
