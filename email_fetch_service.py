# app/email_fetch_service.py
import email
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.gmail_oauth_service import GmailOAuthService
from app.repositories import (
    EmailRepository,
    AttachmentRepository,
    EmailFilterRepository,
    JobRunRepository,
)
from app.config import settings

logger = logging.getLogger(__name__)


class EmailFetchService:
    """ Serviço responsável por: - Conectar no Gmail via IMAP OAuth2 - Buscar emails novos - Aplicar filtros dinâmicos - Salvar emails e anexos no banco + filesystem - Registrar execução em JobRun """

    def __init__(self, gmail_oauth_service: GmailOAuthService):
        self.gmail_oauth_service = gmail_oauth_service
        os.makedirs(settings.attachments_dir, exist_ok=True)

    def _build_search_criteria(self, dynamic_filters: Optional[Dict[str, Any]] = None) -> str:
        """ Monta a string de busca IMAP com base em filtros dinâmicos e filtros da base. """
        criteria_parts = ["UNSEEN"]

        if dynamic_filters:
            sender = dynamic_filters.get("sender")
            subject = dynamic_filters.get("subject")
            keyword = dynamic_filters.get("keyword")

            if sender:
                criteria_parts.append(f'FROM "{sender}"')
            if subject:
                criteria_parts.append(f'SUBJECT "{subject}"')
            if keyword:
                criteria_parts.append(f'TEXT "{keyword}"')

        return " ".join(criteria_parts)

    def fetch_and_store_emails( self, db: Session, dynamic_filters: Optional[Dict[str, Any]] = None, ) -> None:
        """ Lê emails do Gmail (via IMAP OAuth2), aplica filtros, salva emails/anexos, registra JobRun. """
        job_run = JobRunRepository.create(db)
        messages_fetched = 0
        messages_saved = 0

        imap = self.gmail_oauth_service.open_imap_connection()

        try:
            typ, _ = imap.select("INBOX")
            if typ != "OK":
                logger.error("Não foi possível selecionar INBOX: %s", typ)
                JobRunRepository.finish(
                    db,
                    job_run,
                    messages_fetched=0,
                    messages_saved=0,
                    status="error",
                    error_message="Não foi possível selecionar INBOX",
                )
                db.commit()
                return

            search_criteria = self._build_search_criteria(dynamic_filters)
            logger.info("Busca IMAP com critérios: %s", search_criteria)

            typ, data = imap.search(None, *search_criteria.split())
            if typ != "OK":
                logger.error("Erro ao buscar mensagens: %s - %s", typ, data)
                JobRunRepository.finish(
                    db,
                    job_run,
                    messages_fetched=0,
                    messages_saved=0,
                    status="error",
                    error_message=f"Erro ao buscar mensagens: {data}",
                )
                db.commit()
                return

            message_nums = data[0].split()
            messages_fetched = len(message_nums)
            logger.info("Mensagens encontradas: %d", messages_fetched)

            for num in message_nums:
                typ, msg_data = imap.fetch(num, "(RFC822)")
                if typ != "OK":
                    logger.warning("Erro ao fazer fetch da mensagem %s: %s", num, typ)
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                message_id = msg.get("Message-ID")
                if not message_id:
                    logger.warning("Mensagem sem Message-ID, ignorando.")
                    continue

                if EmailRepository.get_by_message_id(db, message_id):
                    logger.debug("Mensagem %s já existe. Ignorando.", message_id)
                    continue

                from_ = msg.get("From")
                to_ = msg.get("To")
                cc_ = msg.get("Cc")
                subject_ = msg.get("Subject")
                date_header = msg.get("Date")

                # Extrair corpo texto
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition") or "")

                        if (
                            content_type == "text/plain"
                            and "attachment" not in content_disposition.lower()
                        ):
                            charset = part.get_content_charset() or "utf-8"
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_text += payload.decode(charset, errors="ignore")
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(charset, errors="ignore")

                received_at = datetime.utcnow()
                if date_header:
                    try:
                        from email.utils import parsedate_to_datetime

                        received_at = parsedate_to_datetime(date_header)
                    except Exception:
                        logger.debug(
                            "Não foi possível converter data do cabeçalho: %s", date_header
                        )

                email_record = EmailRepository.create(
                    db=db,
                    message_id=message_id,
                    sender=from_ or "",
                    recipient=to_,
                    cc=cc_,
                    subject=subject_,
                    body=body_text,
                    received_at=received_at,
                )

                # Anexos
                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition") or "")
                    if "attachment" in content_disposition.lower():
                        filename = part.get_filename()
                        if not filename:
                            continue

                        file_data = part.get_payload(decode=True) or b""
                        mime_type = part.get_content_type()
                        size_bytes = len(file_data)

                        # Cria attachment com nome temporário
                        temp_name = "PENDING"
                        attachment = AttachmentRepository.create(
                            db=db,
                            email_id=email_record.id,
                            filename_original=filename,
                            filename_stored=temp_name,
                            mime_type=mime_type,
                            size_bytes=size_bytes,
                        )

                        stored_name = (
                            f"ID{email_record.id:08d}-{attachment.id:08d}-{filename}"
                        )
                        stored_path = os.path.join(settings.attachments_dir, stored_name)

                        try:
                            with open(stored_path, "wb") as f:
                                f.write(file_data)

                            attachment.filename_stored = stored_name
                            db.add(attachment)
                        except Exception as e:
                            logger.exception("Erro ao salvar anexo: %s", e)
                            AttachmentRepository.delete(db, attachment)
                            db.flush()

                messages_saved += 1

            JobRunRepository.finish(
                db,
                job_run,
                messages_fetched=messages_fetched,
                messages_saved=messages_saved,
                status="success",
                error_message=None,
            )
            db.commit()

        except Exception as e:
            logger.exception("Erro geral no fetch_and_store_emails: %s", e)
            db.rollback()
            JobRunRepository.finish(
                db,
                job_run,
                messages_fetched=messages_fetched,
                messages_saved=messages_saved,
                status="error",
                error_message=str(e),
            )
            db.commit()
        finally:
            try:
                imap.close()
            except Exception:
                pass
            imap.logout()