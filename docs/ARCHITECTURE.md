# Veteran Target Architecture

## High-Level Flow
Frontend (Next.js)
→ Tenant-Aware API Gateway
→ Auth + Session Layer
→ Tenant Isolation Middleware
→ Graph API Sync Services
→ Email Processing Pipeline
→ Embedding Generation
→ Tenant-Specific Vector Storage
→ RAG Retrieval Engine
→ Hallucination Prevention Layer
→ Grounded AI Responses

## Multi-Tenant Model
Required identity dimensions:
- `tenant_id`
- `user_id`
- `workspace_id`
- `collection_name`
- `embedding_namespace`

Isolation rules:
- Every query requires tenant scope.
- Every storage write is tagged with tenant and user ownership.
- Vector retrieval is namespace/collection constrained per user/workspace.
- Chat state and citations are tenant-bound.

## Service Boundaries

### frontend/
- Microsoft OAuth login entry.
- Workspace-scoped chat UI.
- Citation display (email/thread/attachment references).

### backend/
- REST/GraphQL APIs.
- Tenant-aware gateway and policy enforcement.
- Rate limiting, audit logging, RBAC checks.

### ingestion/
- Graph API mailbox sync.
- Attachment extraction and metadata normalization.
- Retry-safe incremental indexing.

### ai-engine/
- Intent detection.
- Retrieval orchestration.
- Evidence verification.
- Citation injection.
- Hallucination filter.

### vector-db/
- Tenant-aware index/query adapters.
- Metadata filtering + reranking interfaces.

### auth/
- OAuth2 token exchange/refresh.
- Encrypted token storage.
- Session lifecycle.

## Required Runtime Retrieval Chain
1. Intent Detection
2. Semantic Retrieval
3. Metadata Validation
4. Reranking
5. Citation Verification
6. LLM Synthesis
7. Citation Injection
8. Hallucination Filter
9. Final Response

## Mandatory Response Contract
Every answer must include:
- evidence sources (email IDs/threads/attachments)
- timestamps
- confidence score
- relevance/evidence quality indicator

If missing evidence:
- “No matching email found.”
- “Insufficient evidence available.”
- “Unable to verify from indexed communications.”
