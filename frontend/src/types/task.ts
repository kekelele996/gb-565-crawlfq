import type { SignalLevel, TaskStatus } from '../constants/enums'

export interface SequenceItem {
  seq: number
  url_id: string
  domain: string
  site_name: string
  raw_url: string
  canonical_url: string
  depth: number
  priority: number
  wait_seconds: number
  aging: number
  depth_penalty: number
  score: number
  starvation_boosted: boolean
  forced_probe: boolean
  status_code: number
  rate_limited: boolean
  backoff_applied_s: number
  latency_ms: number
  token_before: number
  token_after: number
  virtual_time_s: number
}

export interface BackoffEvent {
  seq: number
  domain: string
  site_name: string
  url_id: string
  raw_url: string
  status_code: number
  window_before_s: number
  window_after_s: number
  backoff_until_s: number
  consecutive_429: number
  virtual_time_s: number
}

export interface StarvationBoost {
  seq_at: number
  domain: string
  site_name: string
  url_id: string
  raw_url: string
  wait_seconds: number
  score_before: number
  score_after: number
  virtual_time_s: number
  reason: string
}

export interface DomainStat {
  domain: string
  site_name: string
  qps_quota: number
  crawl_delay_s: number
  max_concurrency: number
  priority: number
  capacity: number
  tokens_remaining: number
  token_ratio: number
  issued: number
  succeeded: number
  rate_limited: number
  effective_qps: number
  backoff_window_s: number
  backoff_until_s: number
  signal: SignalLevel
}

export interface SchedulerResult {
  task_name: string
  seed: number
  window_s: number
  max_sequence: number
  sequence_length: number
  issued: number
  succeeded: number
  rate_limited_count: number
  elapsed_s: number
  sequence: SequenceItem[]
  backoff_events: BackoffEvent[]
  backoff_decays: Array<Record<string, unknown>>
  starvation_boosts: StarvationBoost[]
  blocked_count: number
  blocked: Array<Record<string, unknown>>
  domain_stats: DomainStat[]
  chaos_plan: Array<{ seq: number; domain: string; remark: string }>
  formula: string
  digest: string
  generated_at: string
}

export interface CrawlTask {
  id: string
  name: string
  site_domains: string[]
  concurrency: number
  quota_snapshot: Record<string, Record<string, number>>
  status: TaskStatus
  seed: number
  window_s: number
  max_sequence: number
  scheduled_count: number
  created_by: string
  started_at: string | null
  finished_at: string | null
  created_at: string
  has_result: boolean
  result_summary: {
    sequence_length: number
    rate_limited_count: number
    starvation_count: number
    elapsed_s: number
    digest: string
  } | null
  scheduler_result?: SchedulerResult | null
}

export interface TaskSummary {
  total: number
  queued: number
  running: number
  paused: number
  finished: number
  scheduled_total: number
}

export interface TaskCreatePayload {
  name: string
  site_domains: string[]
  concurrency: number
  window_s: number
  max_sequence: number
  seed: number
}
