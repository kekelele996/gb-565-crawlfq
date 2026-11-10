/** 错误码文案：与 backend/src/constants/error_codes.py 对齐。 */
export const ERROR_MESSAGES: Record<string, string> = {
  'CRF-4010': '请先登录',
  'CRF-4011': '邮箱或密码不正确 / 登录已过期',
  'CRF-4030': '当前角色没有该操作权限',
  'CRF-4040': '目标资源不存在',
  'CRF-4090': '资源状态冲突',
  'CRF-4220': '参数校验失败',
  'CRF-4290': '请求过于频繁，请稍后重试',
  'CRF-5000': '服务内部错误',
}

export const API_PREFIX = '/api'
export const TOKEN_KEY = 'crawlfq_token'
export const BRAND = 'crawlfq'
