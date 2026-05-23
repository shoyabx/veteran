'use client'

import { signOut } from 'next-auth/react'

export function LogoutButton() {
  return (
    <button 
      className="rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200" 
      onClick={() => signOut({ callbackUrl: '/' })}
    >
      Logout
    </button>
  )
}
