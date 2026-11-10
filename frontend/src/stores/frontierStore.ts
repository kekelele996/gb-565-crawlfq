import { defineStore } from 'pinia'
import { fetchExamples, fetchStats, listUrls, previewUrl } from '../api/frontier'
import type { FrontierStats, FrontierUrl, PreviewResult } from '../types/frontier'
import type { ApiError } from '../types/api'

interface FrontierState {
  stats: FrontierStats | null
  items: FrontierUrl[]
  examples: FrontierUrl[]
  total: number
  page: number
  pageSize: number
  selectedId: string
  preview: PreviewResult | null
  loading: boolean
  error: string
  filters: { domain: string; status: string; duplicate: string; q: string }
}

export const useFrontierStore = defineStore('frontier', {
  state: (): FrontierState => ({
    stats: null,
    items: [],
    examples: [],
    total: 0,
    page: 1,
    pageSize: 20,
    selectedId: '',
    preview: null,
    loading: false,
    error: '',
    filters: { domain: '', status: '', duplicate: '', q: '' },
  }),
  getters: {
    selected(state): FrontierUrl | null {
      return state.items.find((item) => item.id === state.selectedId) ?? state.items[0] ?? null
    },
  },
  actions: {
    select(id: string) {
      this.selectedId = id
    },
    async loadStats() {
      try {
        this.stats = await fetchStats()
      } catch (error) {
        this.error = (error as ApiError).message ?? '统计加载失败'
      }
    },
    async loadExamples() {
      try {
        const result = await fetchExamples(3)
        this.examples = result.items
      } catch {
        this.examples = []
      }
    },
    async load(resetPage = false) {
      if (resetPage) this.page = 1
      this.loading = true
      this.error = ''
      try {
        const params = {
          domain: this.filters.domain || undefined,
          status: this.filters.status || undefined,
          duplicate: this.filters.duplicate || undefined,
          q: this.filters.q || undefined,
          page: this.page,
          page_size: this.pageSize,
        }
        const result = await listUrls(params)
        this.items = result.items
        this.total = result.total
        if (!this.items.find((item) => item.id === this.selectedId)) {
          this.selectedId = this.items[0]?.id ?? ''
        }
      } catch (error) {
        this.error = (error as ApiError).message ?? '前沿加载失败'
      } finally {
        this.loading = false
      }
    },
    async runPreview(url: string) {
      this.error = ''
      try {
        this.preview = await previewUrl(url)
        return this.preview
      } catch (error) {
        this.preview = null
        this.error = (error as ApiError).message ?? '规范化失败'
        throw error
      }
    },
  },
})
