import http from './http'
import type { AuditSummary, CoverageAudit } from '../types/audit'

export async function listAudits(): Promise<{ items: CoverageAudit[]; summary: AuditSummary }> {
  const { data } = await http.get('/audits')
  return data
}

export async function runAudit(siteDomain: string, batchLabel?: string): Promise<CoverageAudit> {
  const { data } = await http.post('/audits/run', { site_domain: siteDomain, batch_label: batchLabel })
  return data
}

export async function downloadGapsCsv(auditId?: string): Promise<{ blob: Blob; rows: number }> {
  const url = auditId ? `/audits/${auditId}/gaps.csv` : '/audits/gaps.csv'
  const response = await http.get(url, { responseType: 'blob' })
  const rows = Number(response.headers['x-row-count'] ?? 0)
  return { blob: response.data as Blob, rows }
}
