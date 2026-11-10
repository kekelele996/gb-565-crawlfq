/** 共享枚举前端副本：与 backend/src/constants/enums.py 字面量保持一致。 */
export type RobotsStatus = 'allow' | 'partial' | 'blocked'
export type UrlStatus = 'queued' | 'inflight' | 'done' | 'blocked' | 'failed' | 'folded'
export type UrlSource = 'sitemap' | 'link' | 'seed'
export type TaskStatus = 'queued' | 'running' | 'paused' | 'finished'
export type FetchOrigin = 'seed' | 'simulation'
export type GapReason = 'not_discovered' | 'robots_blocked' | 'fetch_failed' | 'over_quota'
export type SignalLevel = 'green' | 'yellow' | 'red'
export type UserRole = 'admin' | 'engineer' | 'viewer'

export const ROBOTS_LABELS: Record<RobotsStatus, string> = {
  allow: '允许',
  partial: '部分禁止',
  blocked: '全站禁止',
}

export const URL_STATUS_LABELS: Record<UrlStatus, string> = {
  queued: '排队中',
  inflight: '抓取中',
  done: '已抓取',
  blocked: 'robots 禁止',
  failed: '失败',
  folded: '去重折叠',
}

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  queued: '待调度',
  running: '运行中',
  paused: '已暂停',
  finished: '已完成',
}

export const GAP_REASON_LABELS: Record<GapReason, string> = {
  not_discovered: 'sitemap 未发现',
  robots_blocked: 'robots 禁止路径',
  fetch_failed: '抓取失败',
  over_quota: '配额耗尽未抓',
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: '调度主管',
  engineer: '采集工程师',
  viewer: '只读观察员',
}

export const SOURCE_LABELS: Record<UrlSource, string> = {
  sitemap: 'sitemap',
  link: '链接发现',
  seed: '种子',
}

export function signalClass(signal: SignalLevel | string): string {
  return signal === 'green' ? 'sig-green' : signal === 'yellow' ? 'sig-amber' : 'sig-red'
}
