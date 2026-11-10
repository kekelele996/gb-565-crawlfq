export interface FetchRecord {
  id: string
  task_id: string | null
  domain: string
  status_code: number
  latency_ms: number
  bytes: number
  was_duplicate: boolean
  rate_limited: boolean
  backoff_applied_s: number
  origin: string
  fetched_at: string
  signal?: 'green' | 'yellow' | 'red'
}

export interface FetchSummary {
  total: number
  rate_limited: number
  duplicates: number
  by_status: Record<string, number>
  by_origin: Record<string, number>
}

export interface FetchListResult {
  items: FetchRecord[]
  total: number
  page: number
  page_size: number
  summary: FetchSummary
}

export interface FetchTimeline {
  events: FetchRecord[]
  rate_limited_events: FetchRecord[]
  backoff_domains: Array<{
    domain: string
    rate_limited: number
    max_backoff_s: number
    last_at: string | null
  }>
  window: string
}
