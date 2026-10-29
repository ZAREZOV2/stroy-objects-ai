"""REST API модуля RAG."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.rag import AskRequest, AskResponse, DocumentRead
from app.services.rag import ingest as ingest_service
from app.services.rag import ollama as ollama_service

router = APIRouter(prefix="/api/rag", tags=["ИИ-помощник"])


@router.get("/status")
async def rag_status():
    ok = await ollama_service.check_ollama_available()
    return {
        "ollama_available": ok,
        "message": "Ollama доступен — можно генерировать ответы LLM."
        if ok
        else "Ollama недоступен — работает ключевой/векторный поиск без генерации.",
    }


@router.get("/documents", response_model=list[DocumentRead])
async def list_docs(db: AsyncSession = Depends(get_db)):
    rows = await ingest_service.list_documents(db)
    return [
        DocumentRead(
            id=d.id,
            title=d.title,
            filename=d.filename,
            file_type=d.file_type,
            is_demo=d.is_demo,
            chunk_count=cnt,
        )
        for d, cnt in rows
    ]


@router.post("/documents", response_model=DocumentRead, status_code=201)
async def upload_doc(
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    content = await file.read()
    try:
        doc = await ingest_service.ingest_bytes(
            db, title=title, filename=file.filename or "doc.txt", content=content
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    chunks = len(doc.chunks) if doc.chunks else 0
    return DocumentRead(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_type=doc.file_type,
        is_demo=doc.is_demo,
        chunk_count=chunks,
    )


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, db: AsyncSession = Depends(get_db)):
    return await ingest_service.answer_question(db, payload.question)
