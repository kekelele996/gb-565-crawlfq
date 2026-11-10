import { defineStore } from 'pinia'
import { downloadGapsCsv, listAudits, runAudit } from '../api/audits'
import type { AuditSummary, CoverageAudit } from '../types/audit'
import type { ApiError } from '../types/api'

interface AuditsState {
  items: CoverageAudit[]
  summary: AuditSummary | null
  loading: boolean
  running: boolean
  exporting: boolean
  error: string
  lastExport: { rows: number; at: string } | null
}

export const useAuditsStore = defineStore('audits', {
  state: (): AuditsState => ({
    items: [],
    summary: null,
    loading: false,
    running: false,
    exporting: false,
    error: '',
    lastExport: null,
  }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await listAudits()
        this.items = result.items
        this.summary = result.summary
      } catch (error) {
        this.error = (error as ApiError).message ?? '审计加载失败'
      } finally {
        this.loading = false
      }
    },
    async run(siteDomain: string) {
      this.running = true
      this.error = ''
      try {
        await runAudit(siteDomain)
        await this.load()
      } catch (error) {
        this.error = (error as ApiError).message ?? '审计执行失败'
        throw error
      } finally {
        this.running = false
      }
    },
    async exportGaps(auditId?: string) {
      this.exporting = true
      this.error = ''
      try {
        const result = await downloadGapsCsv(auditId)
        const link = document.createElement('a')
        link.href = URL.createObjectURL(result.blob)
        link.download = auditId ? `crawlfq-gaps-${auditId.slice(0, 8)}.csv` : 'crawlfq-gaps-all.csv'
        document.body.appendChild(link)
        link.click()
        link.remove()
        setTimeout(() => URL.revokeObjectURL(link.href), 2000)
        this.lastExport = { rows: result.rows, at: new Date().toISOString() }
        return result
      } catch (error) {
        this.error = (error as ApiError).message ?? '缺口导出失败（只读角色无导出权限）'
        throw error
      } finally {
        this.exporting = false
      }
    },
  },
})
