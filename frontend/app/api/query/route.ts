import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'

export async function POST(req: NextRequest) {
  const session = await auth()
  const user = session?.user

  if (!user || !(user as any).id_token) {
    return NextResponse.json({ error: 'Unauthorized: Missing session or ID token' }, { status: 401 })
  }

  try {
    const body = await req.json()
    const { query, top_k = 10, score_threshold = 0.35, synthesize = true, filters = {} } = body

    if (!query || typeof query !== 'string') {
      return NextResponse.json({ error: 'Query is required and must be a string' }, { status: 400 })
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

    // 1. Submit Query
    const queryRes = await fetch(`${backendUrl}/api/v1/retrieval/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${(user as any).id_token}`
      },
      body: JSON.stringify({
        query,
        top_k,
        score_threshold,
        synthesize,
        filters
      })
    })

    if (!queryRes.ok) {
      const errText = await queryRes.text()
      return NextResponse.json({ error: `Backend query failed: ${errText}` }, { status: queryRes.status })
    }

    const queryData = await queryRes.json()
    const queryId = queryData.query_id

    // 2. Fetch Query Results & Synthesized Answer
    const statusRes = await fetch(`${backendUrl}/api/v1/retrieval/query/${queryId}`, {
      headers: {
        'Authorization': `Bearer ${(user as any).id_token}`
      }
    })

    if (!statusRes.ok) {
      const errText = await statusRes.text()
      return NextResponse.json({ error: `Backend status fetch failed: ${errText}` }, { status: statusRes.status })
    }

    const statusData = await statusRes.json()
    return NextResponse.json(statusData)

  } catch (error: any) {
    console.error('Error proxying query:', error)
    return NextResponse.json({ error: error.message || 'Internal server error' }, { status: 500 })
  }
}
