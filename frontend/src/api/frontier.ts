import http from './http'
import type { FrontierStats, FrontierUrl, PreviewResult } from '../types/frontier'
import type { PageResult } from '../types/api'

export interface FrontierQuery {
  domain?: string
  status?: string
  duplicate?: string
  q?: string
  page?: number
  page_size?: number
}

export async function listUrls(params: FrontierQuery): Promise<PageResult<FrontierUrl>> {
  const { data } = await http.get('/frontier', { params })
  return data
}

export async function fetchStats(): Promise<FrontierStats> {
  const { data } = await http.get('/frontier/stats')
  return data
}

export async function fetchExamples(limit = 3): Promise<{ items: FrontierUrl[] }> {
  const { data } = await http.get('/frontier/examples', { params: { limit } })
  return data
}

export async function previewUrl(url: string): Promise<PreviewResult> {
  const { data } = await http.post('/frontier/preview', { url })
  return data
}
