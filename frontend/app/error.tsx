'use client'

export default function ErrorPage({ error }: { error: Error }) {
  return (
    <main className='mx-auto max-w-xl p-8'>
      <h2 className='text-xl font-semibold'>Something went wrong</h2>
      <p className='text-sm text-red-600 mt-2'>{error.message}</p>
    </main>
  )
}
