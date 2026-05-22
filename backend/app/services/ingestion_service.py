from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.ingestion import Mailbox, SyncState, Email, EmailParticipant, Attachment, IngestionJob, IngestionFailure
from app.models.models import OAuthAccount
from app.services.token_service import get_graph_access_token
from app.services.graph_client import MicrosoftGraphClient, GraphAPIError
from app.services.normalization import normalize_message, normalize_participants
from app.services.attachment_validator import validate_attachment


def assert_mailbox_ownership(db: Session, tenant_id: int, mailbox_id: int) -> Mailbox:
    mailbox = db.scalar(select(Mailbox).where(Mailbox.id == mailbox_id, Mailbox.tenant_id == tenant_id, Mailbox.is_active == True))
    if not mailbox:
        raise ValueError('mailbox_not_found_or_not_owned')
    return mailbox


def create_ingestion_job(db: Session, tenant_id: int, mailbox_id: int, correlation_id: str) -> IngestionJob:
    job = IngestionJob(tenant_id=tenant_id, mailbox_id=mailbox_id, status='queued', correlation_id=correlation_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def run_mailbox_delta_sync(db: Session, tenant_id: int, mailbox_id: int, correlation_id: str, job: IngestionJob | None = None) -> IngestionJob:
    mailbox = assert_mailbox_ownership(db, tenant_id, mailbox_id)
    if job is None:
        job = IngestionJob(tenant_id=tenant_id, mailbox_id=mailbox_id, status='running', correlation_id=correlation_id)
        db.add(job)
        db.commit(); db.refresh(job)
    else:
        job.status = 'running'
        db.commit(); db.refresh(job)

    try:
        oauth = db.scalar(select(OAuthAccount).where(OAuthAccount.user_id == mailbox.user_id, OAuthAccount.provider == 'microsoft'))
        if oauth is None:
            raise ValueError('oauth_account_not_found')

        access = get_graph_access_token(oauth.access_token_encrypted, oauth.refresh_token_encrypted)
        client = MicrosoftGraphClient(access)

        state = db.scalar(select(SyncState).where(SyncState.mailbox_id == mailbox.id))
        delta_link = state.delta_token if state else None

        next_link = None
        while True:
            page = await client.delta_messages_page(delta_link=delta_link if next_link is None else next_link)
            for msg in page.get('value', []):
                data = normalize_message(msg)
                if not data.get('graph_message_id'):
                    continue

                existing = db.scalar(select(Email).where(Email.tenant_id == tenant_id, Email.mailbox_id == mailbox.id, Email.graph_message_id == data['graph_message_id']))
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                    existing.updated_at = datetime.utcnow()
                    email_row = existing
                else:
                    email_row = Email(tenant_id=tenant_id, mailbox_id=mailbox.id, **data)
                    db.add(email_row)
                    db.flush()

                db.query(EmailParticipant).filter(EmailParticipant.email_id == email_row.id).delete()
                for p in normalize_participants(msg):
                    db.add(EmailParticipant(tenant_id=tenant_id, email_id=email_row.id, **p))

                if data['has_attachments'] and not data['is_deleted']:
                    att_next = None
                    while True:
                        att_page = await client.list_attachments(email_row.graph_message_id, next_link=att_next)
                        for a in att_page.get('value', []):
                            ok, reason = validate_attachment(a.get('contentType') or '', int(a.get('size') or 0))
                            rec = db.scalar(select(Attachment).where(Attachment.tenant_id == tenant_id, Attachment.email_id == email_row.id, Attachment.graph_attachment_id == a.get('id')))
                            payload = {
                                'tenant_id': tenant_id,
                                'email_id': email_row.id,
                                'graph_attachment_id': a.get('id'),
                                'file_name': a.get('name') or 'unknown',
                                'content_type': a.get('contentType') or 'application/octet-stream',
                                'size_bytes': int(a.get('size') or 0),
                                'is_supported_type': ok,
                            }
                            if rec:
                                for k, v in payload.items():
                                    setattr(rec, k, v)
                            else:
                                db.add(Attachment(**payload))
                        att_next = att_page.get('@odata.nextLink')
                        if not att_next:
                            break

            next_link = page.get('@odata.nextLink')
            delta_token_new = page.get('@odata.deltaLink')
            if delta_token_new:
                if state is None:
                    state = SyncState(tenant_id=tenant_id, mailbox_id=mailbox.id)
                    db.add(state)
                state.delta_token = delta_token_new
                state.last_sync_at = datetime.utcnow()
                state.mailbox_state = {'cursor_type': 'delta'}
                state.updated_at = datetime.utcnow()
            db.commit()
            if not next_link:
                break

        job.status = 'succeeded'
        job.finished_at = datetime.utcnow()
        db.commit(); db.refresh(job)
        return job

    except (GraphAPIError, Exception) as e:
        db.add(IngestionFailure(tenant_id=tenant_id, job_id=job.id, stage='delta_sync', error_code=getattr(e, 'code', 'ingestion_error'), error_message=str(e), retryable=getattr(e, 'retryable', False)))
        job.status = 'failed'
        job.finished_at = datetime.utcnow()
        db.commit(); db.refresh(job)
        return job
