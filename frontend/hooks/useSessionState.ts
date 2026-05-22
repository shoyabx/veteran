'use client'

import { useSession } from 'next-auth/react'

export function useSessionState() {
  const { data, status } = useSession()
  return {
    session: data,
    loading: status === 'loading',
    authenticated: status === 'authenticated',
  }
}
