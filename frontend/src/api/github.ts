import { api } from './client'
import type { GithubRepo } from '../types'

export async function getGithubRepos(): Promise<GithubRepo[]> {
  const response = await api.get('/github/repos')
  return response.data
}

export async function getCommitSummary(
  customerId: string,
  from: string,
  to: string,
): Promise<{ summary: string | null; commit_count: number; themes: string[] }> {
  const response = await api.get('/github/summary', {
    params: { customer_id: customerId, from, to },
  })
  return response.data
}

/** Marker prefix of an auto-generated Leistungsbeschreibung (safe to overwrite on re-import). */
export const SUMMARY_MARKER = 'Erbrachte Leistungen ('
