# test_gmail_imap.py
import logging
import email

from app.gmail_oauth_service import GmailOAuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Iniciando teste de conexão IMAP com Gmail via OAuth2...")

    gmail_oauth = GmailOAuthService()

    # Abre conexão IMAP autenticada
    imap = gmail_oauth.open_imap_connection()
    logger.info("Conexão IMAP estabelecida com sucesso.")

    try:
        # Seleciona a INBOX
        typ, data = imap.select("INBOX")
        if typ != "OK":
            logger.error("Falha ao selecionar INBOX: %s - %s", typ, data)
            return

        # Busca as últimas 10 mensagens (por exemplo) – aqui uso ALL só para teste
        typ, data = imap.search(None, "ALL")
        if typ != "OK":
            logger.error("Erro ao buscar mensagens: %s - %s", typ, data)
            return

        message_nums = data[0].split()
        logger.info("Total de mensagens na INBOX: %d", len(message_nums))

        # Pega apenas as últimas 5 para exemplo
        last_5 = message_nums[-5:]
        logger.info("Lendo últimas %d mensagens...", len(last_5))

        for num in last_5:
            typ, msg_data = imap.fetch(num, "(RFC822)")
            if typ != "OK":
                logger.warning("Erro ao fazer fetch da mensagem %s: %s", num, typ)
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            message_id = msg.get("Message-ID")
            from_ = msg.get("From")
            subject_ = msg.get("Subject")

            logger.info("Mensagem %s:", num.decode())
            logger.info(" Message-ID: %s", message_id)
            logger.info(" From : %s", from_)
            logger.info(" Subject : %s", subject_)

    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()
        logger.info("Conexão IMAP encerrada.")


if __name__ == "__main__":
    main()