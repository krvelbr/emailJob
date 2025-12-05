import logging
import os
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .config import settings
from .models import EmailFilter, Email, Attachment, JobRun
from .repositories import (
    EmailRepository,
    AttachmentRepository,
    EmailFilterRepository,
    JobRunRepository,
)
from .email_client import EmailClient

logger = logging.getLogger(__name__)


def ensure_attachments_dir():
    os.makedirs(settings.attachments_dir, exist_ok=True)


# ---------- Filtros Dinâmicos ----------
def apply_filters_to_email(email_data: Dict[str, Any], filters: List[EmailFilter]) -> bool:
    """ Retorna True se o email passar em ALGUM filtro ativo (OR entre filtros), cada filtro internamente é AND entre seus campos configurados. """
    if not filters:
        return True  # se não há filtros, aceita todos

    for f in filters:
        if not f.enabled:
            continue
        conds = []
        if f.from_address:
            conds.append(f.from_address.lower() in (email_data["sender"] or "").lower())
        if f.subject_contains:
            conds.append(f.subject_contains.lower() in (email_data["subject"] or "").lower())
        if f.body_contains:
            conds.append(f.body_contains.lower() in (email_data["body"] or "").lower())

        # Se o filtro não tiver nenhuma condição configurada, ignora-o
        if not (f.from_address or f.subject_contains or f.body_contains):
            continue

        # AND interno
        if all(conds):
            return True

    return False


# ---------- Job principal de checagem ----------
def run_email_check_job(db: Session) -> JobRun:
    """ Executa o job de checagem, retorna JobRun. """
    job_run = JobRunRepository.create(db)
    db.commit()  # persiste início do job

    messages_fetched = 0
    messages_saved = 0
    error_message = None
    status_str = "success"

    try:
        ensure_attachments_dir()
        client = EmailClient()
        raw_emails = client.fetch_unseen_emails_raw()
        messages_fetched = len(raw_emails)

        filters = EmailFilterRepository.get_all(db, enabled_only=True)

        for em in raw_emails:
            # Evitar duplicação por message_id
            if not em["message_id"]:
                # se não tem message_id, você pode criar um hash do corpo, mas por simplicidade vamos ignorar
                continue
            if EmailRepository.get_by_message_id(db, em["message_id"]):
                continue

            # aplicar filtros dinâmicos
            if not apply_filters_to_email(em, filters):
                continue

            # Cria Email
            email_obj = EmailRepository.create(
                db,
                message_id=em["message_id"],
                sender=em["sender"],
                recipient=em["recipient"],
                cc=em["cc"],
                subject=em["subject"],
                body=em["body"],
                received_at=em["received_at"],
            )

            # Anexos: regra de gravação com rollback se falhar
            for attach in em["attachments"]:
                _save_attachment_with_rollback(
                    db=db,
                    email_obj=email_obj,
                    filename_original=attach["filename"],
                    mime_type=attach["mime_type"],
                    content=attach["content"],
                    size_bytes=attach["size_bytes"],
                )

            messages_saved += 1

        status_str = "success"
        db.commit()
    except Exception as exc:
        logger.exception("Erro ao executar job de checagem de e-mail")
        db.rollback()
        error_message = str(exc)
        status_str = "error"

    finally:
        # finalizar job_run
        JobRunRepository.finish(
            db,
            job_run=job_run,
            messages_fetched=messages_fetched,
            messages_saved=messages_saved,
            status=status_str,
            error_message=error_message,
        )
        db.commit()

    return job_run


def _save_attachment_with_rollback( db: Session, email_obj: Email, filename_original: str, mime_type: Optional[str], content: bytes, size_bytes: Optional[int], ):
    """ Regras: - primeiro grava metadata no DB (Attachment), com filename_stored provisório - flush para obter attachment.id - monta o nome final: 'ID<email_id>-<attachment_id>_<nome_original>' - atualiza attachment.filename_stored, tenta gravar arquivo em disco - se falhar ao gravar, faz rollback da transação e lança exceção """
    try:
        # Passo 1: cria registro com filename_stored temporário
        temp_name = "temp"
        attachment = AttachmentRepository.create(
            db=db,
            email_id=email_obj.id,
            filename_original=filename_original,
            filename_stored=temp_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        db.flush()  # attachment.id disponível

        stored_filename = f"ID{email_obj.id:08d}-{attachment.id:08d}_{filename_original}"
        attachment.filename_stored = stored_filename
        db.add(attachment)
        db.flush()

        # Passo 2: grava arquivo em disco
        ensure_attachments_dir()
        file_path = os.path.join(settings.attachments_dir, stored_filename)

        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as exc:
            logger.exception("Falha ao gravar arquivo de anexo em disco")
            db.rollback()
            # remover arquivo se parcialmente gravado
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao salvar anexo '{filename_original}' em disco: {exc}",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro ao salvar anexo com rollback")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar anexo '{filename_original}': {exc}",
        )


# ---------- Métricas / Health ----------
def get_job_metrics(db: Session):
    last, total_fetched, total_saved = JobRunRepository.get_aggregated_metrics(db)
    from .schemas import JobMetrics

    return JobMetrics(
        last_run_start=last.started_at if last else None,
        last_run_end=last.finished_at if last else None,
        last_status=last.status if last else None,
        last_error=last.error_message if last else None,
        total_messages_fetched=total_fetched,
        total_messages_saved=total_saved,
    )