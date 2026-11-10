import type { GapReason } from '../constants/enums'

export interface GapEntry {
  url: string
  raw_url: string
  reason: GapReason
  depth: number
}

export interface CoverageAudit {
  id: string
  site_domain: string
  batch_label: string
  sitemap_declared: number
  discovered: number
  fetched: number
  coverage_ratio: number
  coverage_pct: number
  gap_count: number
  created_at: string
  gaps?: GapEntry[]
}

export interface AuditSummary {
  total: number
  declared_total: number
  fetched_total: number
  gap_total: number
  avg_coverage: number
}
