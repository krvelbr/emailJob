# app/gmail_oauth_service.py
import logging
import imaplib
import requests

from app.config import settings

logger = logging.getLogger(__name__)


class GmailOAuthService:
    """ Serviço responsável por: - Obter ACCESS_TOKEN a partir do REFRESH_TOKEN - Abrir conexão IMAP com Gmail via XOAUTH2 """

    def __init__(self):
        self.settings = settings

    def get_access_token(self) -> str:
        """ Usa o REFRESH_TOKEN para obter um ACCESS_TOKEN novo. """
        data = {
            "client_id": self.settings.gmail_client_id,
            "client_secret": self.settings.gmail_client_secret,
            "refresh_token": self.settings.gmail_refresh_token,
            "grant_type": "refresh_token",
        }

        token_url = self.settings.gmail_token_uri
        resp = requests.post(token_url, data=data)

        if resp.status_code != 200:
            logger.error(
                "Falha ao obter access_token do Google: %s - %s",
                resp.status_code,
                resp.text,
            )
            raise RuntimeError("Erro ao obter access token do Google")

        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            logger.error("Resposta do Google sem access_token: %s", payload)
            raise RuntimeError("access_token não encontrado na resposta do Google")

        return access_token

    def open_imap_connection(self) -> imaplib.IMAP4_SSL:
        """ Abre conexão IMAP com Gmail usando OAuth2 (XOAUTH2). Retorna o objeto imaplib.IMAP4_SSL autenticado. """
        access_token = self.get_access_token()

        imap = imaplib.IMAP4_SSL(
            self.settings.gmail_imap_server,
            self.settings.gmail_imap_port,
        )

        def auth_callback(_):
            auth_string = (
                f"user={self.settings.gmail_email}\1"
                f"auth=Bearer {access_token}\1\1"
            )
            return auth_string.encode("utf-8")

        typ, data = imap.authenticate("XOAUTH2", auth_callback)

        if typ != "OK":
            logger.error("Falha na autenticação IMAP XOAUTH2: %s - %s", typ, data)
            raise RuntimeError("Erro na autenticação IMAP XOAUTH2")

        logger.info(
            "Autenticação IMAP XOAUTH2 bem-sucedida para %s",
            self.settings.gmail_email,
        )
        return imap