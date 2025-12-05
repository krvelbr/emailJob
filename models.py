from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from .database import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    sender = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=True)
    cc = Column(String(1024), nullable=True)
    subject = Column(String(1024), nullable=True)
    body = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    attachments = relationship("Attachment", back_populates="email", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    filename_original = Column(String(1024), nullable=False)
    filename_stored = Column(String(1024), nullable=False, unique=True)
    mime_type = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    email = relationship("Email", back_populates="attachments")


class EmailFilter(Base):
    """ Filtros dinâmicos configuráveis via API. Podem ser combinados: por remetente, palavra-chave no assunto/corpo etc. """
    __tablename__ = "email_filters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    enabled = Column(Boolean, default=True, nullable=False)
    from_address = Column(String(255), nullable=True, index=True)
    subject_contains = Column(String(255), nullable=True)
    body_contains = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    messages_fetched = Column(Integer, default=0, nullable=False)
    messages_saved = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="running", nullable=False)
    error_message = Column(Text, nullable=True)