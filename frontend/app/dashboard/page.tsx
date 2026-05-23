import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { LogoutButton } from '@/components/LogoutButton'
import { SessionPanel } from '@/components/SessionPanel'
import { SearchPanel } from '@/components/SearchPanel'

export default async function DashboardPage() {
  const session = await auth()
  if (!session?.user) redirect('/')

  return (
    <div className="min-h-screen bg-[#070A13] text-white">
      {/* Premium Top Navigation Header */}
      <header className="border-b border-slate-800 bg-[#0B0F19]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className="h-7 w-7 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20 text-xs">V</span>
            <span className="font-extrabold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-slate-100 to-slate-300">VETERAN</span>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full">Outlook Intelligence</span>
            <LogoutButton />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-5xl px-6 py-10 space-y-8">
        <div className="space-y-2 border-b border-slate-800/60 pb-6">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-100">
            Protected Dashboard
          </h1>
          <p className="text-sm text-slate-400">
            Secure workspace successfully loaded with verified dynamic Entra ID credentials.
          </p>
        </div>

        <SessionPanel />

        <SearchPanel />
      </main>
    </div>
  )
}
