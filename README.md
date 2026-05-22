# Veteran

Production-grade, multi-tenant, AI-powered Outlook intelligence platform.

## Core Objectives
- Retrieval-grounded answers over indexed Outlook data.
- Strict tenant isolation across data, retrieval, and chat.
- Dual-mode anti-hallucination framework:
  - **Mode 1:** Agent execution safety (build-time guardrails)
  - **Mode 2:** Runtime response safety (user-facing guardrails)
- Local-first development at `/Users/shoyab/Veteran` with GitHub source control at `https://github.com/shoyabx/veteran`.

## Monorepo Structure
- `frontend/` Next.js app
- `backend/` API + orchestration services
- `ai-engine/` RAG synthesis + hallucination filters
- `ingestion/` Graph sync + ETL
- `vector-db/` tenant-aware vector access layer
- `auth/` OAuth/session/token modules
- `infrastructure/` infra config + observability
- `docker/` container definitions
- `scripts/` utility scripts
- `docs/` architecture and policies
- `tests/` unit/integration/e2e suites
- `.github/workflows/` CI/CD

## Git Workflow
```bash
git init
git remote add origin https://github.com/shoyabx/veteran.git
git checkout -b develop
```

Branch model:
- `main`
- `develop`
- `feature/*`
- `hotfix/*`

## CI/CD
See `.github/workflows/ci.yml` for:
- lint
- tests
- Docker build validation
- deployment manifest validation

## Safety Directives
See:
- `docs/ARCHITECTURE.md`
- `docs/ANTI_HALLUCINATION_POLICY.md`
