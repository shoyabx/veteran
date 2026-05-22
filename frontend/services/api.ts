export interface VerifyResponse {
  user_id: number;
  tenant_id: number;
  email: string;
  role: string;
  auth_provider: string;
}

export async function verifyBackendSession(accessToken: string): Promise<VerifyResponse> {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
  const res = await fetch(`${base}/api/v1/auth/verify`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  })

  if (!res.ok) throw new Error(`Auth verification failed: ${res.status}`)
  return res.json() as Promise<VerifyResponse>
}
