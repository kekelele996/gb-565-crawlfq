import http from './http'
import type { SeedSite, SiteSummary, SiteUpdatePayload } from '../types/site'

export async function listSites(): Promise<{ items: SeedSite[]; summary: SiteSummary }> {
  const { data } = await http.get('/sites')
  return data
}

export async function updateSite(
  siteId: string,
  payload: SiteUpdatePayload,
): Promise<{ site: SeedSite; changes: Record<string, unknown>; changed: boolean }> {
  const { data } = await http.patch(`/sites/${siteId}`, payload)
  return data
}
