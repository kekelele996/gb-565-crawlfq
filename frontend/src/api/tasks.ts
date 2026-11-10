import http from './http'
import type { CrawlTask, TaskCreatePayload, TaskSummary } from '../types/task'

export async function listTasks(): Promise<{ items: CrawlTask[]; summary: TaskSummary }> {
  const { data } = await http.get('/tasks')
  return data
}

export async function createTask(payload: TaskCreatePayload): Promise<CrawlTask> {
  const { data } = await http.post('/tasks', payload)
  return data
}

export async function getTask(taskId: string): Promise<CrawlTask> {
  const { data } = await http.get(`/tasks/${taskId}`)
  return data
}

export async function simulateTask(taskId: string): Promise<CrawlTask> {
  const { data } = await http.post(`/tasks/${taskId}/simulate`)
  return data
}
