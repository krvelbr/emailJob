# app/repositories.py
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from . import models


class EmailRepository:
    @staticmethod
    def get_by_message_id(db: Session, message_id: str) -> Optional[models.Email]:
        stmt = select(models.Email).where(models.Email.message_id == message_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def create( db: Session, message_id: str, sender: str, recipient: Optional[str], cc: Optional[str], subject: Optional[str], body: Optional[str], received_at, ) -> models.Email:
        email = models.Email(
            message_id=message_id,
            sender=sender,
            recipient=recipient,
            cc=cc,
            subject=subject,
            body=body,
            received_at=received_at,
        )
        db.add(email)
        db.flush()  # para obter email.id
        return email

    @staticmethod
    def get_paginated( db: Session, page: int, page_size: int, sender: Optional[str] = None, subject: Optional[str] = None, has_attachments: Optional[bool] = None, include_deleted: bool = False, ) -> Tuple[List[models.Email], int]:
        # SUGESTÃO: Para evitar duplicação de código, a construção da query
        # poderia ser feita em uma função auxiliar.
        query_filters = []
        if not include_deleted:
            # Usar 'is_' para comparações com True/False/None é mais idiomático
            query_filters.append(models.Email.is_deleted.is_(False))
        if sender:
            query_filters.append(models.Email.sender.ilike(f"%{sender}%"))
        if subject:
            query_filters.append(models.Email.subject.ilike(f"%{subject}%"))
        if has_attachments is not None:
            if has_attachments:
                query_filters.append(models.Email.attachments.any())
            else:
                query_filters.append(~models.Email.attachments.any())

        # Query para os itens paginados
        stmt = select(models.Email).where(*query_filters)
        
        # Query para a contagem total, reutilizando os mesmos filtros
        total_stmt = select(func.count(models.Email.id)).where(*query_filters)
        
        total = db.execute(total_stmt).scalar_one()
        
        stmt = stmt.order_by(
            models.Email.received_at.desc().nullslast(),
            models.Email.id.desc(),
        ).offset((page - 1) * page_size).limit(page_size)
        
        items = db.execute(stmt).scalars().all()
        return items, total

    @staticmethod
    def get_by_id(db: Session, email_id: int) -> Optional[models.Email]:
        stmt = select(models.Email).where(models.Email.id == email_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def soft_delete(db: Session, email: models.Email):
        email.is_deleted = True
        db.add(email)

    @staticmethod
    def hard_delete(db: Session, email: models.Email):
        db.delete(email)


class AttachmentRepository:
    @staticmethod
    def create( db: Session, email_id: int, filename_original: str, filename_stored: str, mime_type: Optional[str], size_bytes: Optional[int], ) -> models.Attachment:
        attachment = models.Attachment(
            email_id=email_id,
            filename_original=filename_original,
            filename_stored=filename_stored,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        db.add(attachment)
        db.flush()  # obter attachment.id
        return attachment

    @staticmethod
    def get_by_id(db: Session, attachment_id: int) -> Optional[models.Attachment]:
        stmt = select(models.Attachment).where(models.Attachment.id == attachment_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def delete(db: Session, attachment: models.Attachment):
        db.delete(attachment)


class EmailFilterRepository:
    @staticmethod
    def create(db: Session, **kwargs) -> models.EmailFilter:
        filt = models.EmailFilter(**kwargs)
        db.add(filt)
        db.flush()
        return filt

    @staticmethod
    def get_all(db: Session, enabled_only: bool = False) -> List[models.EmailFilter]:
        stmt = select(models.EmailFilter)
        if enabled_only:
            # SUGESTÃO: Usar 'is_(True)' é mais explícito e recomendado pelo SQLAlchemy
            stmt = stmt.where(models.EmailFilter.enabled.is_(True))
        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_by_id(db: Session, filter_id: int) -> Optional[models.EmailFilter]:
        stmt = select(models.EmailFilter).where(models.EmailFilter.id == filter_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def delete(db: Session, filt: models.EmailFilter):
        db.delete(filt)


class JobRunRepository:
    @staticmethod
    def create(db: Session) -> models.JobRun:
        job_run = models.JobRun()
        db.add(job_run)
        db.flush()
        return job_run

    @staticmethod
    def finish( db: Session, job_run: models.JobRun, messages_fetched: int, messages_saved: int, status: str, error_message: Optional[str] = None, ):
        job_run.finished_at = datetime.utcnow()
        job_run.messages_fetched = messages_fetched
        job_run.messages_saved = messages_saved
        job_run.status = status
        job_run.error_message = error_message
        db.add(job_run)

    @staticmethod
    def get_last(db: Session) -> Optional[models.JobRun]:
        stmt = select(models.JobRun).order_by(models.JobRun.id.desc()).limit(1)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_aggregated_metrics(db: Session):
        total_fetched = db.execute(
            select(func.coalesce(func.sum(models.JobRun.messages_fetched), 0))
        ).scalar_one()
        total_saved = db.execute(
            select(func.coalesce(func.sum(models.JobRun.messages_saved), 0))
        ).scalar_one()
        last = JobRunRepository.get_last(db)
        return last, total_fetched, total_saved
