export interface ApiError {
  code: string
  message: string
  detail?: string
  trace_id?: string | null
  status?: number
  extra?: Record<string, unknown>
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
