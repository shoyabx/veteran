from dataclasses import dataclass

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0


class IngestionQueue:
    """Queue abstraction placeholder for Phase 1B.
    Current implementation uses DB-backed queued jobs for deterministic tenant-safe scheduling.
    """

    def enqueue(self, mailbox_id: int, tenant_id: int) -> dict:
        return {'mailbox_id': mailbox_id, 'tenant_id': tenant_id, 'status': 'queued'}
