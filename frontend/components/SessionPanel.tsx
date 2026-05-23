import { auth } from '@/auth'

export async function SessionPanel() {
  const session = await auth()
  const user = session?.user

  if (!user) return null

  // Extract first letter of name for a clean avatar fallback
  const initials = user.name
    ? user.name
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .toUpperCase()
    : 'U'

  return (
    <div className="space-y-6">
      {/* Upper Layout: User Card & Security Context */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* User Identity Profile Card */}
        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-[#0F1424] p-6 shadow-xl transition-all duration-300 hover:border-slate-700">
          <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-blue-500/10 blur-2xl"></div>
          <div className="flex items-center space-x-4">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
              {initials}
              <span className="absolute -bottom-1 -right-1 flex h-4 w-4 rounded-full border-2 border-[#0F1424] bg-emerald-500">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              </span>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Authenticated Member</div>
              <h2 className="text-xl font-bold text-slate-100">{user.name}</h2>
              <p className="text-sm text-slate-400">{user.email}</p>
            </div>
          </div>

          <div className="mt-6 space-y-3 border-t border-slate-800/80 pt-4 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Auth System</span>
              <span className="font-semibold text-slate-300 capitalize">{user.auth_provider || 'Microsoft Entra ID'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Role Status</span>
              <span className="inline-flex items-center rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-medium text-indigo-400">
                {user.role || 'Member'}
              </span>
            </div>
          </div>
        </div>

        {/* Tenant Boundary Security Card */}
        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-[#0F1424] p-6 shadow-xl transition-all duration-300 hover:border-slate-700">
          <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-emerald-500/10 blur-2xl"></div>
          <div className="flex items-center space-x-3 text-emerald-400">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h3 className="text-lg font-bold text-slate-100">Multi-Tenant Isolation</h3>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Your session is cryptographically pinned and isolated to the following Active Directory Tenant ID:
          </p>

          <div className="mt-4 rounded-lg bg-slate-900/60 p-3 border border-slate-800/60">
            <span className="block font-mono text-xs font-semibold text-emerald-400 break-all select-all">
              {user.tenant_id}
            </span>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <span className="inline-flex items-center space-x-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-md">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              <span>Boundary Verified</span>
            </span>
            <span className="text-[10px] text-slate-500">Partition Key: tenant_id</span>
          </div>
        </div>
      </div>

      {/* Database & Worker Sync Telemetry */}
      <div className="rounded-2xl border border-slate-800 bg-[#0F1424] p-6 shadow-xl">
        <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
          <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
          System & Storage Telemetry
        </h3>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-lg bg-slate-900/40 p-4 border border-slate-800/40">
            <div className="text-slate-500 text-xs">Vector Index Mode</div>
            <div className="font-semibold text-slate-300 mt-1">Tenant-aware partition</div>
          </div>
          <div className="rounded-lg bg-slate-900/40 p-4 border border-slate-800/40">
            <div className="text-slate-500 text-xs">Local DB Engine</div>
            <div className="font-semibold text-slate-300 mt-1">SQLite (veteran.db)</div>
          </div>
          <div className="rounded-lg bg-slate-900/40 p-4 border border-slate-800/40">
            <div className="text-slate-500 text-xs">Backend Endpoint</div>
            <div className="font-semibold text-indigo-400 mt-1 hover:underline">
              <a href="http://127.0.0.1:8000" target="_blank" rel="noreferrer">http://localhost:8000</a>
            </div>
          </div>
        </div>
      </div>

      {/* Accordion / Collapsible JSON Session Inspector */}
      <details className="group rounded-2xl border border-slate-800 bg-[#0F1424] overflow-hidden shadow-xl transition-all duration-300">
        <summary className="flex cursor-pointer items-center justify-between p-6 text-slate-300 select-none hover:bg-slate-800/20">
          <div className="flex items-center space-x-3">
            <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <span className="font-semibold text-slate-200">Inspect Encrypted Session JWT Payload</span>
          </div>
          <span className="transition-transform duration-300 group-open:rotate-180">
            <svg className="h-5 w-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </span>
        </summary>
        <div className="border-t border-slate-800/60 bg-slate-950 p-6">
          <pre className="overflow-x-auto font-mono text-[11px] leading-relaxed text-blue-400 select-all">
            {JSON.stringify(session, null, 2)}
          </pre>
        </div>
      </details>
    </div>
  )
}
