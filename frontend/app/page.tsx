import Link from 'next/link'
import { LoginButton } from '@/components/LoginButton'

export default function HomePage() {
  return (
    <main className='mx-auto max-w-2xl p-8 space-y-4'>
      <h1 className='text-2xl font-bold'>Veteran</h1>
      <p>Phase 1A: Microsoft OAuth + tenant-aware authentication foundation.</p>
      <LoginButton />
      <Link href='/dashboard' className='underline block'>Go to dashboard</Link>
    </main>
  )
}
