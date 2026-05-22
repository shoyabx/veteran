import { auth } from '@/auth'

export async function SessionPanel() {
  const session = await auth()
  return (
    <pre className='rounded bg-gray-100 p-4 text-xs overflow-auto'>
      {JSON.stringify(session?.user ?? null, null, 2)}
    </pre>
  )
}
