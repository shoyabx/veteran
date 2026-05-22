import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { LogoutButton } from '@/components/LogoutButton'
import { SessionPanel } from '@/components/SessionPanel'

export default async function DashboardPage() {
  const session = await auth()
  if (!session?.user) redirect('/')

  return (
    <main className='mx-auto max-w-3xl p-8 space-y-4'>
      <h1 className='text-2xl font-bold'>Protected Dashboard</h1>
      <p className='text-sm text-gray-600'>Tenant-aware session context loaded.</p>
      <SessionPanel />
      <LogoutButton />
    </main>
  )
}
