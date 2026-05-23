import NextAuth from 'next-auth'
import Microsoft from 'next-auth/providers/microsoft-entra-id'

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: 'jwt' },
  providers: [
    Microsoft({
      clientId: process.env.AZURE_CLIENT_ID!,
      clientSecret: process.env.AZURE_CLIENT_SECRET!,
      issuer: `https://login.microsoftonline.com/${process.env.AZURE_TENANT_ID}/v2.0`,
      authorization: { params: { scope: 'openid profile email User.Read Mail.Read Calendars.Read offline_access' } },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.user_id = String(profile.sub || token.sub)
        token.tenant_id = String((profile as any).tid || 'default')
        token.role = 'member'
        token.auth_provider = 'microsoft'
        token.email = token.email || profile.email || ''
        token.access_token = account.access_token
        token.id_token = account.id_token
      }
      return token
    },
    async session({ session, token }) {
      session.user = {
        ...session.user,
        user_id: String(token.user_id || token.sub || ''),
        tenant_id: String(token.tenant_id || ''),
        role: (token.role as string) || 'member',
        auth_provider: 'microsoft',
        email: String(token.email || session.user?.email || ''),
        access_token: String(token.access_token || ''),
        id_token: String(token.id_token || ''),
      } as any
      return session
    },
  },
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === 'production' ? '__Secure-veteran.session-token' : 'veteran.session-token',
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: process.env.NODE_ENV === 'production' },
    },
  },
})
