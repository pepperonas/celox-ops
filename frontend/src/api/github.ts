import { api } from './client'
import type { GithubRepo } from '../types'

export async function getGithubRepos(): Promise<GithubRepo[]> {
  const response = await api.get('/github/repos')
  return response.data
}
