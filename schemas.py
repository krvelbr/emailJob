from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# --------- Attachments ---------
class AttachmentBase(BaseModel):
    id: int
    email_id: int
    filename_original: str
    filename_stored: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True


# --------- Emails ---------
class EmailBase(BaseModel):
    id: int
    message_id: str
    sender: str
    recipient: Optional[str]
    cc: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    received_at: Optional[datetime]
    created_at: datetime
    is_deleted: bool

    class Config:
        orm_mode = True


class EmailDetail(EmailBase):
    attachments: List[AttachmentBase] = []


# --------- Filters ---------
class EmailFilterCreate(BaseModel):
    name: str
    from_address: Optional[str] = None
    subject_contains: Optional[str] = None
    body_contains: Optional[str] = None
    enabled: bool = True


class EmailFilterUpdate(BaseModel):
    from_address: Optional[str] = None
    subject_contains: Optional[str] = None
    body_contains: Optional[str] = None
    enabled: Optional[bool] = None


class EmailFilterOut(BaseModel):
    id: int
    name: str
    from_address: Optional[str]
    subject_contains: Optional[str]
    body_contains: Optional[str]
    enabled: bool
    created_at: datetime

    class Config:
        orm_mode = True


# --------- Job / Metrics ---------
class JobMetrics(BaseModel):
    last_run_start: Optional[datetime]
    last_run_end: Optional[datetime]
    last_status: Optional[str]
    last_error: Optional[str]
    total_messages_fetched: int
    total_messages_saved: int


class TriggerJobResponse(BaseModel):
    job_run_id: int
    status: str
    started_at: datetime


# --------- Pagination ---------
class EmailListItem(EmailBase):
    pass


class PaginatedEmails(BaseModel):
    items: List[EmailListItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool