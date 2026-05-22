from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class IndexMailboxRequest(BaseModel):
    mailbox_id: int
    provider: str = 'openai'
    model_name: str = 'text-embedding-3-small'

class IndexJobResponse(BaseModel):
    job_id: int
    status: str

class IndexJobStatusResponse(BaseModel):
    job_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
