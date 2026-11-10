import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin } from '../api/auth'
import { TOKEN_KEY } from '../constants/messages'
import type { User, UserRole } from '../types/user'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
  error: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) ?? '',
    user: null,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
    role: (state): UserRole => (state.user?.role ?? 'viewer') as UserRole,
    displayName: (state): string => state.user?.display_name ?? '',
    roleLabel: (state): string => state.user?.role_label ?? '',
    permissions: (state): string[] => state.user?.permissions ?? [],
  },
  actions: {
    can(permission: string): boolean {
      return (this.user?.permissions ?? []).includes(permission)
    },
    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await apiLogin(email, password)
        this.token = result.access_token
        this.user = result.user
        localStorage.setItem(TOKEN_KEY, result.access_token)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async restore() {
      if (!this.token) return
      try {
        const result = await fetchMe()
        this.user = result.user
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
