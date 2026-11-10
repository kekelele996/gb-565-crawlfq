import { defineStore } from 'pinia'
import { listSites, updateSite } from '../api/sites'
import type { SeedSite, SiteSummary, SiteUpdatePayload } from '../types/site'

interface SitesState {
  items: SeedSite[]
  summary: SiteSummary | null
  selectedId: string
  loading: boolean
  saving: boolean
  error: string
  lastChange: string
}

export const useSitesStore = defineStore('sites', {
  state: (): SitesState => ({
    items: [],
    summary: null,
    selectedId: '',
    loading: false,
    saving: false,
    error: '',
    lastChange: '',
  }),
  getters: {
    selected(state): SeedSite | null {
      return state.items.find((item) => item.id === state.selectedId) ?? state.items[0] ?? null
    },
  },
  actions: {
    select(id: string) {
      this.selectedId = id
    },
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await listSites()
        this.items = result.items
        this.summary = result.summary
        if (!this.selectedId && result.items.length) {
          this.selectedId = result.items[0].id
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '站点加载失败'
      } finally {
        this.loading = false
      }
    },
    async save(siteId: string, payload: SiteUpdatePayload) {
      this.saving = true
      this.error = ''
      try {
        const result = await updateSite(siteId, payload)
        const index = this.items.findIndex((item) => item.id === siteId)
        if (index >= 0) this.items[index] = result.site
        this.lastChange = JSON.stringify(result.changes)
        await this.load()
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '保存失败'
        throw error
      } finally {
        this.saving = false
      }
    },
  },
})
