from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from typing import Optional

from .database import Base, engine, get_db
from .models import Email, Attachment
from .repositories import (
    EmailRepository,
    AttachmentRepository,
    EmailFilterRepository,
)
from .schemas import (
    EmailDetail,
    PaginatedEmails,
    EmailFilterCreate,
    EmailFilterUpdate,
    EmailFilterOut,
    JobMetrics,
    TriggerJobResponse,
)
from .services import get_job_metrics, run_email_check_job
from .scheduler import start_scheduler, shutdown_scheduler
from .logging_conf import configure_logging
from .config import settings

import os

# Configura logging
configure_logging()

# Cria as tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Email Background Job API",
    description=""" API para gerenciamento de um job em segundo plano que verifica uma caixa de email a cada X minutos, filtra mensagens, armazena emails e anexos em SQLite/pasta local e fornece endpoints para gestão, métricas, filtros dinâmicos, download de anexos e interface web de controle. """,
    version="1.0.0",
)

# Interface web
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """ Interface web básica de gestão dos endpoints (HTML/JS). """
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


# ---------- Eventos de inicialização / finalização ----------
@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_scheduler()


# ---------- Métricas / Healthcheck ----------
@app.get("/metrics", response_model=JobMetrics, tags=["Health & Metrics"])
def read_metrics(db: Session = Depends(get_db)):
    """ Retorna métricas do job: - Última execução (início/fim) - Status da última execução - Erro da última execução (se houver) - Total de mensagens buscadas e salvas """
    return get_job_metrics(db)


@app.get("/health", tags=["Health & Metrics"])
def health():
    """ Endpoint simples de healthcheck da API. """
    return {"status": "ok"}


# ---------- Job manual ----------
@app.post("/job/trigger", response_model=TriggerJobResponse, tags=["Job"])
def trigger_job(db: Session = Depends(get_db)):
    """ Executa o job de checagem de email imediatamente, sem aguardar o agendamento. """
    job_run = run_email_check_job(db)
    return TriggerJobResponse(
        job_run_id=job_run.id,
        status=job_run.status,
        started_at=job_run.started_at,
    )


# ---------- Emails ----------
@app.get("/emails", response_model=PaginatedEmails, tags=["Emails"])
def list_emails( page: int = 1, page_size: int = 10, sender: Optional[str] = None, subject: Optional[str] = None, has_attachments: Optional[bool] = None, include_deleted: bool = False, db: Session = Depends(get_db), ):
    """ Lista emails com paginação avançada e filtros opcionais via query params: - `page` / `page_size` - `sender` (contém) - `subject` (contém) - `has_attachments` (true/false) - `include_deleted` (inclui/exclui emails marcados como deletados) """
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="page e page_size devem ser >= 1")

    items, total = EmailRepository.get_paginated(
        db=db,
        page=page,
        page_size=page_size,
        sender=sender,
        subject=subject,
        has_attachments=has_attachments,
        include_deleted=include_deleted,
    )
    has_prev = page > 1
    has_next = (page * page_size) < total
    return PaginatedEmails(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_previous=has_prev,
    )


@app.get("/emails/{email_id}", response_model=EmailDetail, tags=["Emails"])
def get_email(email_id: int, db: Session = Depends(get_db)):
    """ Retorna os detalhes de um email, incluindo anexos associados. """
    email = EmailRepository.get_by_id(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    return email


@app.delete("/emails/{email_id}", status_code=204, tags=["Emails"])
def delete_email( email_id: int, hard_delete: bool = False, db: Session = Depends(get_db), ):
    """ Deleta um email. - Se `hard_delete=false` (padrão): marca como deletado (soft delete). - Se `hard_delete=true`: remove definitivamente (inclui anexos, pois há CASCADE). """
    email = EmailRepository.get_by_id(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")

    if hard_delete:
        EmailRepository.hard_delete(db, email)
    else:
        EmailRepository.soft_delete(db, email)

    db.commit()
    return


# ---------- Anexos ----------
@app.get("/attachments/{attachment_id}/download", response_class=FileResponse, tags=["Attachments"])
def download_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """ Download direto de um anexo pelo ID. """
    attachment = AttachmentRepository.get_by_id(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")

    file_path = os.path.join(settings.attachments_dir, attachment.filename_stored)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo de anexo não encontrado em disco")

    filename = attachment.filename_original or "attachment"
    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type or "application/octet-stream",
        filename=filename,
    )


@app.delete("/attachments/{attachment_id}", status_code=204, tags=["Attachments"])
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """ Deleta um anexo do banco e do disco. """
    attachment = AttachmentRepository.get_by_id(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")

    file_path = os.path.join(settings.attachments_dir, attachment.filename_stored)
    # Remove do DB
    AttachmentRepository.delete(db, attachment)
    db.commit()

    # Remove do disco (se existir)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        # Não quebra a API se falhar, mas poderia logar
        pass

    return


# ---------- Filtros Dinâmicos ----------
@app.get("/filters", response_model=list[EmailFilterOut], tags=["Filters"])
def list_filters(db: Session = Depends(get_db)):
    """ Lista todos os filtros dinâmicos configurados. """
    return EmailFilterRepository.get_all(db, enabled_only=False)


@app.post("/filters", response_model=EmailFilterOut, status_code=201, tags=["Filters"])
def create_filter(payload: EmailFilterCreate, db: Session = Depends(get_db)):
    """ Cria um filtro dinâmico para seleção de emails. """
    filt = EmailFilterRepository.create(
        db=db,
        name=payload.name,
        from_address=payload.from_address,
        subject_contains=payload.subject_contains,
        body_contains=payload.body_contains,
        enabled=payload.enabled,
    )
    db.commit()
    db.refresh(filt)
    return filt


@app.put("/filters/{filter_id}", response_model=EmailFilterOut, tags=["Filters"])
def update_filter(filter_id: int, payload: EmailFilterUpdate, db: Session = Depends(get_db)):
    """ Atualiza um filtro dinâmico existente (campos parciais). """
    filt = EmailFilterRepository.get_by_id(db, filter_id)
    if not filt:
        raise HTTPException(status_code=404, detail="Filtro não encontrado")

    if payload.from_address is not None:
        filt.from_address = payload.from_address
    if payload.subject_contains is not None:
        filt.subject_contains = payload.subject_contains
    if payload.body_contains is not None:
        filt.body_contains = payload.body_contains
    if payload.enabled is not None:
        filt.enabled = payload.enabled

    db.add(filt)
    db.commit()
    db.refresh(filt)
    return filt


@app.delete("/filters/{filter_id}", status_code=204, tags=["Filters"])
def delete_filter(filter_id: int, db: Session = Depends(get_db)):
    """ Remove um filtro dinâmico. """
    filt = EmailFilterRepository.get_by_id(db, filter_id)
    if not filt:
        raise HTTPException(status_code=404, detail="Filtro não encontrado")

    EmailFilterRepository.delete(db, filt)
    db.commit()
    return