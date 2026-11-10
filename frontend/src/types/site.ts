import type { RobotsStatus } from '../constants/enums'

export interface SeedSite {
  id: string
  domain: string
  name: string
  robots_status: RobotsStatus
  robots_disallow: string[]
  robots_allow: string[]
  crawl_delay_s: number
  qps_quota: number
  max_concurrency: number
  priority: number
  sitemap_declared: number
  enabled: boolean
  last_audited_at: string | null
}

export interface SiteSummary {
  total: number
  allow: number
  partial: number
  blocked: number
  enabled: number
  total_qps: number
}

export interface SiteUpdatePayload {
  qps_quota?: number
  crawl_delay_s?: number
  max_concurrency?: number
  priority?: number
  enabled?: boolean
  robots_status?: RobotsStatus
}
