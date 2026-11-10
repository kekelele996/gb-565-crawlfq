import type { UrlStatus } from '../constants/enums'

export interface FrontierUrl {
  id: string
  domain: string
  site_name: string
  raw_url: string
  canonical_url: string
  fingerprint: string
  fingerprint_short: string
  source: string
  depth: number
  priority_score: number
  status: UrlStatus
  wait_seconds: number
  is_duplicate: boolean
  folded_into_id: string | null
  change_reasons: string[]
  discovered_at: string
}

export interface DomainFoldStat {
  domain: string
  name: string
  raw: number
  unique: number
  folded: number
  queued: number
  done: number
  blocked: number
}

export interface BloomStats {
  bits: number
  k: number
  inserted: number
  set_bits: number
  load: number
  false_positive_rate: number
  false_positive_pct: number
  hit_checks: number
  algorithm: string
}

export interface FrontierStats {
  raw: number
  unique: number
  folded: number
  status_counts: Record<string, number>
  by_domain: DomainFoldStat[]
  reason_histogram: Record<string, number>
  bloom: BloomStats
  formula: string
}

export interface PreviewResult {
  raw_url: string
  canonical_url: string
  fingerprint: string
  change_reasons: string[]
  changed: boolean
  char_saved: number
  scheme: string
  host: string
  path: string
  query: string
  bloom_hit: boolean
  is_duplicate: boolean
  existing: FrontierUrl | null
}
