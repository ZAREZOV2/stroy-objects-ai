"""REST API для реестра строительных объектов."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.object import ObjectStatus
from app.schemas.object import DashboardStats, HistoryRead, ObjectCreate, ObjectRead, ObjectUpdate
from app.services import excel as excel_service
from app.services import objects as object_service

router = APIRouter(prefix="/api/objects", tags=["Объекты"])


def _to_read(obj, *, include_history: bool = False) -> ObjectRead:
    history: list[HistoryRead] = []
    if include_history:
        history = [HistoryRead.model_validate(h) for h in obj.history]
    return ObjectRead(
        id=obj.id,
        name=obj.name,
        object_type=obj.object_type,
        municipality=obj.municipality,
        address=obj.address,
        contractor=obj.contractor,
        status=obj.status,
        planned_start=obj.planned_start,
        planned_end=obj.planned_end,
        actual_end=obj.actual_end,
        budget_rub=obj.budget_rub,
        spent_rub=obj.spent_rub,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        is_overdue=obj.is_overdue(date.today()),
        budget_execution_pct=obj.budget_execution_pct,
        history=history,
    )


@router.get("", response_model=list[ObjectRead])
async def api_list_objects(
    db: AsyncSession = Depends(get_db),
    status: ObjectStatus | None = None,
    municipality: str | None = None,
    overdue: bool = Query(False, description="Только просроченные"),
    skip: int = 0,
    limit: int = Query(100, le=500),
):
    items = await object_service.list_objects(
        db, status=status, municipality=municipality, overdue_only=overdue, skip=skip, limit=limit
    )
    return [_to_read(o) for o in items]


@router.get("/dashboard", response_model=DashboardStats)
async def api_dashboard(db: AsyncSession = Depends(get_db)):
    stats = await object_service.dashboard_stats(db)
    return DashboardStats(
        by_status=stats["by_status"],
        total_budget=stats["total_budget"],
        total_spent=stats["total_spent"],
        overdue_count=stats["overdue_count"],
        overdue_ids=stats["overdue_ids"],
    )


@router.get("/export")
async def api_export(
    db: AsyncSession = Depends(get_db),
    status: ObjectStatus | None = None,
    municipality: str | None = None,
    overdue: bool = False,
):
    items = await object_service.list_objects(
        db, status=status, municipality=municipality, overdue_only=overdue, limit=5000
    )
    data = excel_service.objects_to_excel(items)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=objects_export.xlsx"},
    )


@router.post("/import")
async def api_import(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = await file.read()
    created, errors = await excel_service.import_file(db, content, file.filename or "import.xlsx")
    return {"created": created, "errors": errors}


@router.get("/{object_id}", response_model=ObjectRead)
async def api_get_object(object_id: int, db: AsyncSession = Depends(get_db)):
    obj = await object_service.get_object(db, object_id)
    if not obj:
        raise HTTPException(404, "Объект не найден")
    return _to_read(obj, include_history=True)


@router.post("", response_model=ObjectRead, status_code=201)
async def api_create_object(payload: ObjectCreate, db: AsyncSession = Depends(get_db)):
    obj = await object_service.create_object(db, payload)
    return _to_read(obj)


@router.patch("/{object_id}", response_model=ObjectRead)
async def api_update_object(
    object_id: int, payload: ObjectUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await object_service.get_object(db, object_id)
    if not obj:
        raise HTTPException(404, "Объект не найден")
    obj = await object_service.update_object(db, obj, payload)
    obj = await object_service.get_object(db, object_id)
    return _to_read(obj, include_history=True)


@router.delete("/{object_id}", status_code=204)
async def api_delete_object(object_id: int, db: AsyncSession = Depends(get_db)):
    obj = await object_service.get_object(db, object_id)
    if not obj:
        raise HTTPException(404, "Объект не найден")
    await object_service.delete_object(db, obj)
