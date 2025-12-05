# app/scheduler.py
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.gmail_oauth_service import GmailOAuthService
from app.email_fetch_service import EmailFetchService
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _run_email_job():
    """ Função que será executada pelo APScheduler: - Abre uma sessão de banco - Executa o serviço de fetch - Garante fechamento da sessão """
    db = SessionLocal()
    try:
        gmail_oauth = GmailOAuthService()
        service = EmailFetchService(gmail_oauth_service=gmail_oauth)
        service.fetch_and_store_emails(db=db)
    except Exception as e:
        logger.exception("Erro ao executar job de email: %s", e)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        func=_run_email_job,
        trigger="interval",
        minutes=15,
        id="email_fetch_job",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler iniciado (job de email a cada 15 minutos).")


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler desligado.")
        _scheduler = None