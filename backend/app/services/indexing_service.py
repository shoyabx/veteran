from __future__ import annotations
from datetime import datetime
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import select
from qdrant_client.http import models as qmodels

from app.models.ingestion import Email, Attachment, Mailbox, AttachmentStorageRef
from app.models.indexing import (
    EmbeddingJob, EmbeddingFailure, IndexedChunk, VectorIndexState, AttachmentChunk,
    ParserFailure, EmbeddingUsageLog, IndexingMetric,
)
from app.services.chunking import DeterministicChunker
from app.services.embedding_provider import OpenAIEmbeddingProvider, EmbeddingProviderError
from app.services.qdrant_client import TenantQdrant
from app.services.attachment_parsers import parse_attachment, AttachmentParserError
from app.services.attachment_storage import LocalAttachmentStorage, AttachmentStorageError
from app.services.telemetry import Timer, log_telemetry
from app.core.config import settings


def create_embedding_job(db: Session, tenant_id: int, mailbox_id: int, provider: str, model_name: str, correlation_id: str) -> EmbeddingJob:
    job = EmbeddingJob(tenant_id=tenant_id, mailbox_id=mailbox_id, status='queued', provider=provider, model_name=model_name, correlation_id=correlation_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def assert_mailbox_scope(db: Session, tenant_id: int, mailbox_id: int) -> Mailbox:
    mailbox = db.scalar(select(Mailbox).where(Mailbox.id == mailbox_id, Mailbox.tenant_id == tenant_id, Mailbox.is_active == True))
    if mailbox is None:
        raise ValueError('mailbox_not_found_or_not_owned')
    return mailbox


def _estimate_cost_micro(tokens: int) -> int:
    return int((tokens / 1000.0) * settings.EMBEDDING_COST_PER_1K_USD * 1_000_000)


async def run_embedding_job(db: Session, job: EmbeddingJob) -> EmbeddingJob:
    job.status = 'running'
    db.commit()
    db.refresh(job)

    t_total = Timer.begin()
    try:
        mailbox = assert_mailbox_scope(db, job.tenant_id, job.mailbox_id)
        chunker = DeterministicChunker(
            model_name=job.model_name,
            max_context_tokens=settings.EMBEDDING_CONTEXT_TOKENS,
            reserved_headroom=settings.EMBEDDING_RESERVED_HEADROOM,
        )
        provider = OpenAIEmbeddingProvider(settings.OPENAI_API_KEY, batch_size=settings.EMBEDDING_BATCH_SIZE)
        qdrant = TenantQdrant(settings.QDRANT_URL, settings.QDRANT_API_KEY or None)
        storage = LocalAttachmentStorage(settings.ATTACHMENT_STORAGE_PATH, settings.ATTACHMENT_MAX_SIZE_BYTES)

        state = db.scalar(select(VectorIndexState).where(VectorIndexState.tenant_id == job.tenant_id, VectorIndexState.mailbox_id == mailbox.id))
        after_id = state.last_indexed_email_id if state and state.last_indexed_email_id else 0

        # --- A. RECONCILE DELETED EMAILS (PURGE FROM QDRANT & DB) ---
        deleted_emails = db.scalars(
            select(Email).where(
                Email.tenant_id == job.tenant_id,
                Email.mailbox_id == mailbox.id,
                Email.is_deleted == True
            )
        ).all()
        for de in deleted_emails:
            chunk_exists = db.scalar(select(IndexedChunk).where(IndexedChunk.tenant_id == job.tenant_id, IndexedChunk.email_id == de.id))
            if chunk_exists:
                try:
                    qdrant.delete_vectors_by_email(job.tenant_id, de.id)
                except Exception as q_err:
                    db.add(EmbeddingFailure(
                        tenant_id=job.tenant_id,
                        job_id=job.id,
                        stage='deleted_email_reconciliation',
                        error_code='qdrant_delete_failed',
                        error_message=str(q_err),
                        retryable=True
                    ))
                    continue

                db.query(IndexedChunk).filter(IndexedChunk.tenant_id == job.tenant_id, IndexedChunk.email_id == de.id).delete()
                de_att_ids = db.scalars(select(Attachment.id).where(Attachment.email_id == de.id)).all()
                if de_att_ids:
                    db.query(AttachmentChunk).filter(AttachmentChunk.tenant_id == job.tenant_id, AttachmentChunk.attachment_id.in_(de_att_ids)).delete()

        # --- B. PROCESS MODIFIED AND NEW EMAILS ---
        emails_to_index = []
        if state and state.last_indexed_at:
            modified = db.scalars(
                select(Email).where(
                    Email.tenant_id == job.tenant_id,
                    Email.mailbox_id == mailbox.id,
                    Email.is_deleted == False,
                    Email.updated_at > state.last_indexed_at
                )
            ).all()
            for me in modified:
                try:
                    qdrant.delete_vectors_by_email(job.tenant_id, me.id)
                except Exception as q_err:
                    db.add(EmbeddingFailure(
                        tenant_id=job.tenant_id,
                        job_id=job.id,
                        stage='modified_email_reconciliation',
                        error_code='qdrant_delete_failed',
                        error_message=str(q_err),
                        retryable=True
                    ))
                    continue

                db.query(IndexedChunk).filter(IndexedChunk.tenant_id == job.tenant_id, IndexedChunk.email_id == me.id).delete()
                me_att_ids = db.scalars(select(Attachment.id).where(Attachment.email_id == me.id)).all()
                if me_att_ids:
                    db.query(AttachmentChunk).filter(AttachmentChunk.tenant_id == job.tenant_id, AttachmentChunk.attachment_id.in_(me_att_ids)).delete()

                emails_to_index.append(me)

        new_emails = db.scalars(
            select(Email).where(
                Email.tenant_id == job.tenant_id,
                Email.mailbox_id == mailbox.id,
                Email.id > after_id,
                Email.is_deleted == False
            ).order_by(Email.id.asc()).limit(100)
        ).all()
        emails_to_index.extend(new_emails)

        # Deduplicate to prevent processing the same email twice
        seen_ids = set()
        emails = []
        for e in emails_to_index:
            if e.id not in seen_ids:
                seen_ids.add(e.id)
                emails.append(e)

        all_chunks = []
        lineage = []
        content_hash_builder = hashlib.sha256()

        for e in emails:
            text = (e.body_text or e.body_html or '').strip()
            if text:
                chunks = chunker.chunk_text(text=text, lineage_key=f'email:{job.tenant_id}:{e.id}:{e.updated_at}')
                for c in chunks:
                    all_chunks.append(c.text)
                    lineage.append((e, None, c))
                    content_hash_builder.update(c.checksum.encode())

            atts = db.scalars(select(Attachment).where(Attachment.tenant_id == job.tenant_id, Attachment.email_id == e.id, Attachment.is_supported_type == True)).all()
            for a in atts:
                storage_ref = db.scalar(select(AttachmentStorageRef).where(AttachmentStorageRef.tenant_id == job.tenant_id, AttachmentStorageRef.attachment_id == a.id))
                if not storage_ref:
                    continue
                try:
                    real_path = storage.resolve(job.tenant_id, storage_ref.storage_key)
                    p_timer = Timer.begin()
                    a_text = parse_attachment(
                        real_path,
                        a.content_type,
                        timeout_seconds=settings.ATTACHMENT_PARSER_TIMEOUT_SECONDS,
                        max_chars=settings.ATTACHMENT_PARSER_MAX_CHARS,
                    )
                    db.add(IndexingMetric(
                        tenant_id=job.tenant_id,
                        job_id=job.id,
                        metric_name='parser_latency_ms',
                        metric_value=float(p_timer.elapsed_ms()),
                        tags={'attachment_id': a.id, 'mime_type': a.content_type},
                        correlation_id=job.correlation_id,
                    ))
                except (AttachmentParserError, AttachmentStorageError) as err:
                    db.add(ParserFailure(
                        tenant_id=job.tenant_id,
                        job_id=job.id,
                        attachment_id=a.id,
                        mime_type=a.content_type,
                        error_code='attachment_parse_error',
                        error_message=str(err),
                        correlation_id=job.correlation_id,
                    ))
                    continue

                a_chunks = chunker.chunk_text(text=a_text, lineage_key=f'attachment:{job.tenant_id}:{a.id}:{e.updated_at}')
                for c in a_chunks:
                    all_chunks.append(c.text)
                    lineage.append((e, a, c))
                    content_hash_builder.update(c.checksum.encode())
                    existing_att_chunk = db.scalar(select(AttachmentChunk).where(AttachmentChunk.tenant_id == job.tenant_id, AttachmentChunk.attachment_id == a.id, AttachmentChunk.chunk_id == c.chunk_id))
                    if existing_att_chunk:
                        existing_att_chunk.chunk_text = c.text
                        existing_att_chunk.chunk_checksum = c.checksum
                        existing_att_chunk.source_start_offset = c.start_offset
                        existing_att_chunk.source_end_offset = c.end_offset
                        existing_att_chunk.token_count = c.token_count
                    else:
                        db.add(AttachmentChunk(
                            tenant_id=job.tenant_id,
                            attachment_id=a.id,
                            chunk_id=c.chunk_id,
                            chunk_text=c.text,
                            chunk_checksum=c.checksum,
                            source_start_offset=c.start_offset,
                            source_end_offset=c.end_offset,
                            token_count=c.token_count,
                        ))

        content_hash = content_hash_builder.hexdigest() if all_chunks else None
        if state and content_hash and state.last_content_hash == content_hash:
            job.status = 'succeeded'
            job.finished_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
            return job

        if not all_chunks:
            job.status = 'succeeded'
            job.finished_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
            return job

        embed_timer = Timer.begin()
        embed = await provider.embed(all_chunks, model_name=job.model_name)
        vector_size = len(embed.vectors[0])
        collection = qdrant.ensure_collection(job.tenant_id, vector_size=vector_size)

        points = []
        for idx, vec in enumerate(embed.vectors):
            e, a, c = lineage[idx]
            vector_id = f'{job.tenant_id}:{c.chunk_id}'
            payload = {
                'tenant_id': job.tenant_id,
                'user_id': mailbox.user_id,
                'mailbox_id': mailbox.id,
                'email_id': e.id,
                'conversation_id': e.conversation_id,
                'attachment_id': a.id if a else None,
                'chunk_id': c.chunk_id,
                'chunk_checksum': c.checksum,
                'source_start_offset': c.start_offset,
                'source_end_offset': c.end_offset,
                'token_count': c.token_count,
                'source_timestamp': (e.received_at or e.sent_at).isoformat() if (e.received_at or e.sent_at) else None,
                'content_version': c.content_version,
                'semantic_version': '2.1',
                'sync_version': int(e.id),
            }
            points.append(qmodels.PointStruct(id=vector_id, vector=vec, payload=payload))

            existing = db.scalar(select(IndexedChunk).where(IndexedChunk.tenant_id == job.tenant_id, IndexedChunk.chunk_id == c.chunk_id))
            if existing:
                if existing.chunk_checksum != c.checksum:
                    existing.content_version += 1
                existing.chunk_text = c.text
                existing.chunk_checksum = c.checksum
                existing.source_start_offset = c.start_offset
                existing.source_end_offset = c.end_offset
                existing.token_count = c.token_count
                existing.vector_id = vector_id
                existing.semantic_version = '2.1'
            else:
                db.add(IndexedChunk(
                    tenant_id=job.tenant_id, user_id=mailbox.user_id, mailbox_id=mailbox.id, email_id=e.id,
                    attachment_id=a.id if a else None, conversation_id=e.conversation_id, chunk_id=c.chunk_id,
                    chunk_text=c.text, chunk_checksum=c.checksum,
                    source_start_offset=c.start_offset, source_end_offset=c.end_offset,
                    token_count=c.token_count, source_timestamp=(e.received_at or e.sent_at), vector_id=vector_id, content_version=1,
                    semantic_version='2.1',
                ))

        q_timer = Timer.begin()
        qdrant.upsert_vectors(job.tenant_id, points)

        if state is None:
            state = VectorIndexState(tenant_id=job.tenant_id, mailbox_id=mailbox.id)
            db.add(state)
        state.last_indexed_email_id = emails[-1].id if emails else state.last_indexed_email_id
        state.last_indexed_at = datetime.utcnow()
        state.last_content_hash = content_hash
        state.checkpoint_payload = {'collection': collection, 'indexed_chunks': len(points)}
        state.updated_at = datetime.utcnow()

        db.add(EmbeddingUsageLog(
            tenant_id=job.tenant_id,
            job_id=job.id,
            provider=job.provider,
            model_name=job.model_name,
            prompt_tokens=embed.token_usage,
            estimated_cost_usd_micro=_estimate_cost_micro(embed.token_usage),
            batch_count=max(1, (len(all_chunks) + settings.EMBEDDING_BATCH_SIZE - 1) // settings.EMBEDDING_BATCH_SIZE),
            correlation_id=job.correlation_id,
        ))
        db.add(IndexingMetric(tenant_id=job.tenant_id, job_id=job.id, metric_name='embedding_latency_ms', metric_value=float(embed.latency_ms), tags=None, correlation_id=job.correlation_id))
        db.add(IndexingMetric(tenant_id=job.tenant_id, job_id=job.id, metric_name='qdrant_latency_ms', metric_value=float(q_timer.elapsed_ms()), tags=None, correlation_id=job.correlation_id))
        db.add(IndexingMetric(tenant_id=job.tenant_id, job_id=job.id, metric_name='indexing_throughput_chunks', metric_value=float(len(points)), tags=None, correlation_id=job.correlation_id))
        db.add(IndexingMetric(tenant_id=job.tenant_id, job_id=job.id, metric_name='job_latency_ms', metric_value=float(t_total.elapsed_ms()), tags=None, correlation_id=job.correlation_id))

        log_telemetry('indexing_job_succeeded', {'tenant_id': job.tenant_id, 'job_id': job.id, 'correlation_id': job.correlation_id, 'chunk_count': len(points)})

        job.status = 'succeeded'
        job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job
    except EmbeddingProviderError as e:
        db.add(EmbeddingFailure(tenant_id=job.tenant_id, job_id=job.id, stage='embedding', error_code=e.code, error_message=e.message, retryable=e.retryable))
        job.retry_count += 1
        job.status = 'failed'
        job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job
    except Exception as e:
        db.add(EmbeddingFailure(tenant_id=job.tenant_id, job_id=job.id, stage='indexing', error_code='indexing_error', error_message=str(e), retryable=True))
        job.retry_count += 1
        job.status = 'failed'
        job.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job
