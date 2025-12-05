import email
import imaplib
from typing import List, Dict, Any
from datetime import datetime
from .config import settings
from email.header import decode_header, make_header


class EmailClient:
    def __init__(self):
        self.host = settings.email_host
        self.port = settings.email_port
        self.user = settings.email_user
        self.password = settings.email_password
        self.use_ssl = settings.email_use_ssl

    def _connect(self):
        if self.use_ssl:
            #mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail = self.gmail_oauth_service.open_imap_connection()
        else:
            #mail = imaplib.IMAP4(self.host, self.port)
            mail = self.gmail_oauth_service.open_imap_connection()
        mail.login(self.user, self.password)
        return mail

    def fetch_unseen_emails_raw(self) -> List[Dict[str, Any]]:
        """ Exemplo: busca todos os emails recentes. Você pode refinar para buscar por data ou por flag 'UNSEEN'. """
        mail = self._connect()
        try:
            mail.select("INBOX")
            # Buscar todos: "ALL" ou somente não lidos: "UNSEEN"
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                return []

            email_ids = messages[0].split()
            result = []
            for num in email_ids:
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(data[0][1])

                message_id = msg.get("Message-ID", "").strip()
                sender = str(make_header(decode_header(msg.get("From", ""))))
                recipient = str(make_header(decode_header(msg.get("To", ""))))
                cc = str(make_header(decode_header(msg.get("Cc", "")))) if msg.get("Cc") else None
                subject = str(make_header(decode_header(msg.get("Subject", "")))) if msg.get("Subject") else None
                date_raw = msg.get("Date")
                try:
                    received_at = datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(date_raw)))
                except Exception:
                    received_at = None

                # Corpo
                body_text = ""
                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        content_disposition = str(part.get("Content-Disposition", ""))
                        content_type = part.get_content_type()
                        if "attachment" in content_disposition.lower():
                            filename = part.get_filename()
                            if filename:
                                filename_decoded = str(make_header(decode_header(filename)))
                            else:
                                filename_decoded = "unknown"
                            payload = part.get_payload(decode=True) or b""
                            attachments.append(
                                {
                                    "filename": filename_decoded,
                                    "mime_type": content_type,
                                    "content": payload,
                                    "size_bytes": len(payload),
                                }
                            )
                        elif content_type == "text/plain" and "attachment" not in content_disposition.lower():
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or "utf-8"
                                try:
                                    body_text += payload.decode(charset, errors="replace")
                                except Exception:
                                    body_text += payload.decode(errors="replace")
                else:
                    if msg.get_content_type() == "text/plain":
                        payload = msg.get_payload(decode=True)
                        charset = msg.get_content_charset() or "utf-8"
                        if payload:
                            try:
                                body_text = payload.decode(charset, errors="replace")
                            except Exception:
                                body_text = payload.decode(errors="replace")

                result.append(
                    {
                        "message_id": message_id,
                        "sender": sender,
                        "recipient": recipient,
                        "cc": cc,
                        "subject": subject,
                        "body": body_text,
                        "received_at": received_at,
                        "attachments": attachments,
                    }
                )
            return result
        finally:
            try:
                mail.logout()
            except Exception:
                pass