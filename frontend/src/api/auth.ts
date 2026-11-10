import http from './http'
import type { AuthResult, User } from '../types/user'

export async function login(email: string, password: string): Promise<AuthResult> {
  const { data } = await http.post('/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<{ user: User }> {
  const { data } = await http.get('/auth/me')
  return data
}
