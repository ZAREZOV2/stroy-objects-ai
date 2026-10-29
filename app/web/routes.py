"""HTML-интерфейс (Jinja2)."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.object import ObjectStatus, ObjectType
from app.schemas.object import ObjectCreate, ObjectUpdate
from app.services import excel as excel_service
from app.services import objects as object_service
from app.services.rag import ingest as ingest_service
from app.services.rag import ollama as ollama_service

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    stats = await object_service.dashboard_stats(db)
    ollama_ok = await ollama_service.check_ollama_available()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "ollama_ok": ollama_ok,
            "status_labels": list(stats["by_status"].keys()),
            "status_values": list(stats["by_status"].values()),
            "budget_pct": float(stats["total_spent"] / stats["total_budget"] * 100)
            if stats["total_budget"] > 0
            else 0,
        },
    )


@router.get("/objects", response_class=HTMLResponse)
async def objects_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    municipality: str | None = None,
    overdue: str | None = None,
):
    st = ObjectStatus(status) if status else None
    items = await object_service.list_objects(
        db,
        status=st,
        municipality=municipality or None,
        overdue_only=overdue == "1",
        limit=500,
    )
    return templates.TemplateResponse(
        request,
        "objects/list.html",
        {
            "objects": items,
            "filters": {"status": status, "municipality": municipality, "overdue": overdue},
            "statuses": ObjectStatus,
            "today": date.today(),
        },
    )


@router.get("/objects/new", response_class=HTMLResponse)
async def object_new(request: Request):
    return templates.TemplateResponse(
        request,
        "objects/form.html",
        {"object": None, "types": ObjectType, "statuses": ObjectStatus, "action": "create"},
    )


@router.get("/objects/{object_id}", response_class=HTMLResponse)
async def object_detail(object_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    obj = await object_service.get_object(db, object_id)
    if not obj:
        return RedirectResponse("/objects", status_code=303)
    return templates.TemplateResponse(
        request,
        "objects/detail.html",
        {"object": obj, "today": date.today()},
    )


@router.get("/objects/{object_id}/edit", response_class=HTMLResponse)
async def object_edit(object_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    obj = await object_service.get_object(db, object_id)
    if not obj:
        return RedirectResponse("/objects", status_code=303)
    return templates.TemplateResponse(
        request,
        "objects/form.html",
        {"object": obj, "types": ObjectType, "statuses": ObjectStatus, "action": "edit"},
    )


@router.post("/objects/save")
async def object_save(
    db: AsyncSession = Depends(get_db),
    object_id: int | None = Form(None),
    name: str = Form(...),
    object_type: ObjectType = Form(...),
    municipality: str = Form(...),
    address: str = Form(...),
    contractor: str = Form(...),
    status: ObjectStatus = Form(...),
    planned_start: str = Form(""),
    planned_end: str = Form(""),
    actual_end: str = Form(""),
    budget_rub: str = Form("0"),
    spent_rub: str = Form("0"),
):
    def parse_d(s: str):
        return date.fromisoformat(s) if s else None

    payload_data = {
        "name": name,
        "object_type": object_type,
        "municipality": municipality,
        "address": address,
        "contractor": contractor,
        "status": status,
        "planned_start": parse_d(planned_start),
        "planned_end": parse_d(planned_end),
        "actual_end": parse_d(actual_end),
        "budget_rub": Decimal(budget_rub.replace(",", ".") or "0"),
        "spent_rub": Decimal(spent_rub.replace(",", ".") or "0"),
    }
    if object_id:
        obj = await object_service.get_object(db, object_id)
        if obj:
            await object_service.update_object(db, obj, ObjectUpdate(**payload_data))
            return RedirectResponse(f"/objects/{object_id}", status_code=303)
    else:
        obj = await object_service.create_object(db, ObjectCreate(**payload_data))
        return RedirectResponse(f"/objects/{obj.id}", status_code=303)
    return RedirectResponse("/objects", status_code=303)


@router.post("/objects/import")
async def objects_import(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = await file.read()
    await excel_service.import_file(db, content, file.filename or "import.xlsx")
    return RedirectResponse("/objects", status_code=303)


@router.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request, db: AsyncSession = Depends(get_db)):
    docs = await ingest_service.list_documents(db)
    ollama_ok = await ollama_service.check_ollama_available()
    return templates.TemplateResponse(
        request,
        "assistant.html",
        {
            "documents": docs,
            "ollama_ok": ollama_ok,
            "answer": None,
            "question": "",
        },
    )


@router.post("/assistant", response_class=HTMLResponse)
async def assistant_ask(
    request: Request,
    db: AsyncSession = Depends(get_db),
    question: str = Form(""),
    title: str = Form(""),
    file: UploadFile | None = None,
):
    if not question.strip() and not (file and file.filename):
        return RedirectResponse("/assistant", status_code=303)

    if file and file.filename:
        content = await file.read()
        await ingest_service.ingest_bytes(
            db, title=title or file.filename, filename=file.filename, content=content
        )
        return RedirectResponse("/assistant", status_code=303)

    result = await ingest_service.answer_question(db, question)
    docs = await ingest_service.list_documents(db)
    ollama_ok = await ollama_service.check_ollama_available()
    return templates.TemplateResponse(
        request,
        "assistant.html",
        {
            "documents": docs,
            "ollama_ok": ollama_ok,
            "answer": result,
            "question": question,
        },
    )
