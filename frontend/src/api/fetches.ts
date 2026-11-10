import http from './http'
import type { FetchListResult, FetchTimeline } from '../types/fetch'

export interface FetchQuery {
  domain?: string
  status_code?: number | null
  origin?: string
  rate_limited?: boolean | null
  page?: number
  page_size?: number
}

export async function listFetches(params: FetchQuery): Promise<FetchListResult> {
  const { data } = await http.get('/fetches', { params })
  return data
}

export async function fetchTimeline(limit = 60): Promise<FetchTimeline> {
  const { data } = await http.get('/fetches/timeline', { params: { limit } })
  return data
}
