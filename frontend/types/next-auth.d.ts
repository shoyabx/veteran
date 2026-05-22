import 'next-auth'
import 'next-auth/jwt'

declare module 'next-auth' {
  interface Session {
    user: {
      user_id: string
      tenant_id: string
      email: string
      role: string
      auth_provider: string
      name?: string | null
    }
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    user_id?: string
    tenant_id?: string
    role?: string
    auth_provider?: string
    access_token?: string
  }
}
