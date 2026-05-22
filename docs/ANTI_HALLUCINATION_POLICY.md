# Dual-Mode Hallucination Prevention Policy

## Mode 1: Agent Execution Safety (Build-Time)

### Always
- Validate APIs against official docs before integration.
- Use typed schemas (Pydantic, strict TypeScript, OpenAPI contracts).
- Verify SDK capabilities before using methods.
- Add response validation and explicit error handling.
- Log failures with trace IDs and context.
- Block on ambiguity and request confirmation.

### Never
- Invent routes/endpoints.
- Fabricate schemas.
- Assume Graph API behavior without verification.
- Simulate successful responses.
- Suppress or swallow integration failures.

### Required Integration Safety Layer
- Request schema validation
- Response schema validation
- Retry with backoff
- Circuit-breaking/failure thresholds
- Structured logging + alerting

## Mode 2: Runtime Response Safety (User-Facing)

### Must
- Be retrieval-grounded from indexed artifacts only.
- Include citations (email/thread/attachment references + timestamps).
- Provide confidence/relevance scoring.
- Run evidence-consistency checks before responding.

### Must Not
- Invent commitments, people, meetings, dates, or timelines.
- Infer unsupported intent/context.
- Produce speculative summaries without evidence.

## Hallucination Filter Gate
Block output when any are detected:
- Unsupported claim
- Missing citation
- Fabricated entity
- Weak semantic match below threshold
- Timeline inference without source proof

On block:
1. Regenerate strictly from evidence
2. If still insufficient, return explicit unknown response
