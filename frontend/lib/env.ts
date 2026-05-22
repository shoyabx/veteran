const required = ['NEXTAUTH_SECRET', 'NEXTAUTH_URL', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID'] as const

export function validateFrontendEnv() {
  const missing = required.filter((k) => !process.env[k])
  if (missing.length) throw new Error(`Missing required env vars: ${missing.join(', ')}`)
}
