'use client'

import { signIn } from 'next-auth/react'

export function LoginButton() {
  return (
    <button className='rounded bg-black px-4 py-2 text-white' onClick={() => signIn('microsoft-entra-id', { callbackUrl: '/dashboard' })}>
      Sign in with Microsoft
    </button>
  )
}
