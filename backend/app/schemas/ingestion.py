from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class MailboxCreateRequest(BaseModel):
    provider_mailbox_id: str
    email_address: EmailStr

class MailboxResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    provider: str
    provider_mailbox_id: str
    email_address: str

class SyncStartRequest(BaseModel):
    mailbox_id: int
    mode: Literal['delta', 'full'] = 'delta'

class SyncStartResponse(BaseModel):
    job_id: int
    status: str

class IngestionStatusResponse(BaseModel):
    job_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
