import { defineStore } from 'pinia'
import { fetchTimeline, listFetches } from '../api/fetches'
import type { FetchListResult, FetchRecord, FetchSummary, FetchTimeline } from '../types/fetch'
import type { ApiError } from '../types/api'

interface FetchesState {
  items: FetchRecord[]
  summary: FetchSummary | null
  timeline: FetchTimeline | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  error: string
  filters: { domain: string; code: string; origin: string; rateLimited: string }
}

export const useFetchesStore = defineStore('fetches', {
  state: (): FetchesState => ({
    items: [],
    summary: null,
    timeline: null,
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    error: '',
    filters: { domain: '', code: '', origin: '', rateLimited: '' },
  }),
  actions: {
    async load(resetPage = false) {
      if (resetPage) this.page = 1
      this.loading = true
      this.error = ''
      try {
        const result: FetchListResult = await listFetches({
          domain: this.filters.domain || undefined,
          status_code: this.filters.code ? Number(this.filters.code) : undefined,
          origin: this.filters.origin || undefined,
          rate_limited: this.filters.rateLimited ? this.filters.rateLimited === 'yes' : undefined,
          page: this.page,
          page_size: this.pageSize,
        })
        this.items = result.items
        this.total = result.total
        this.summary = result.summary
      } catch (error) {
        this.error = (error as ApiError).message ?? '抓取记录加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadTimeline(limit = 60) {
      try {
        this.timeline = await fetchTimeline(limit)
      } catch (error) {
        this.error = (error as ApiError).message ?? '时间线加载失败'
      }
    },
  },
})
