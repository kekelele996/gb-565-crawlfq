import { defineStore } from 'pinia'
import { createTask, getTask, listTasks, simulateTask } from '../api/tasks'
import type { CrawlTask, TaskCreatePayload, TaskSummary } from '../types/task'
import type { ApiError } from '../types/api'

interface TasksState {
  items: CrawlTask[]
  summary: TaskSummary | null
  current: CrawlTask | null
  loading: boolean
  simulating: boolean
  error: string
}

export const useTasksStore = defineStore('tasks', {
  state: (): TasksState => ({
    items: [],
    summary: null,
    current: null,
    loading: false,
    simulating: false,
    error: '',
  }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await listTasks()
        this.items = result.items
        this.summary = result.summary
      } catch (error) {
        this.error = (error as ApiError).message ?? '任务加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(taskId: string) {
      this.loading = true
      this.error = ''
      try {
        this.current = await getTask(taskId)
      } catch (error) {
        this.error = (error as ApiError).message ?? '任务详情加载失败'
      } finally {
        this.loading = false
      }
    },
    async simulate(taskId: string) {
      this.simulating = true
      this.error = ''
      try {
        const result = await simulateTask(taskId)
        this.current = result
        return result
      } catch (error) {
        this.error = (error as ApiError).message ?? '调度模拟失败'
        throw error
      } finally {
        this.simulating = false
      }
    },
    async create(payload: TaskCreatePayload) {
      this.error = ''
      try {
        const result = await createTask(payload)
        await this.load()
        return result
      } catch (error) {
        this.error = (error as ApiError).message ?? '创建任务失败'
        throw error
      }
    },
  },
})
