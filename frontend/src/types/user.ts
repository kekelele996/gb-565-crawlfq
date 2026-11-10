import type { UserRole } from '../constants/enums'

export interface User {
  id: string
  email: string
  display_name: string
  role: UserRole
  role_label: string
  permissions: string[]
  is_active: boolean
  last_login_at: string | null
}

export interface AuthResult {
  access_token: string
  token: string
  token_type: string
  expires_in: number
  user: User
}
