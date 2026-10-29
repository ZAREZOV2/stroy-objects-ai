"""Бизнес-логика CRUD и истории изменений объектов."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.object import ConstructionObject, ObjectHistory, ObjectStatus
from app.schemas.object import ObjectCreate, ObjectUpdate

TRACKED_FIELDS = (
    "name",
    "object_type",
    "municipality",
    "address",
    "contractor",
    "status",
    "planned_start",
    "planned_end",
    "actual_end",
    "budget_rub",
    "spent_rub",
)


def _serialize_value(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):  # enum
        return str(value.value)
    return str(value)


async def list_objects(
    db: AsyncSession,
    *,
    status: ObjectStatus | None = None,
    municipality: str | None = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[ConstructionObject]:
    q = select(ConstructionObject).order_by(ConstructionObject.id)
    if status:
        q = q.where(ConstructionObject.status == status)
    if municipality:
        q = q.where(ConstructionObject.municipality.ilike(f"%{municipality}%"))
    result = await db.execute(q.offset(skip).limit(limit))
    items = list(result.scalars().all())
    if overdue_only:
        today = date.today()
        items = [o for o in items if o.is_overdue(today)]
    return items


async def get_object(db: AsyncSession, object_id: int) -> ConstructionObject | None:
    q = (
        select(ConstructionObject)
        .where(ConstructionObject.id == object_id)
        .options(selectinload(ConstructionObject.history))
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def create_object(db: AsyncSession, data: ObjectCreate) -> ConstructionObject:
    obj = ConstructionObject(**data.model_dump())
    db.add(obj)
    await db.flush()
    db.add(
        ObjectHistory(
            object_id=obj.id,
            field_name="created",
            old_value=None,
            new_value=obj.name,
            comment="Создание записи",
        )
    )
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_object(
    db: AsyncSession, obj: ConstructionObject, data: ObjectUpdate
) -> ConstructionObject:
    updates = data.model_dump(exclude_unset=True)
    for field, new_val in updates.items():
        old_val = getattr(obj, field)
        if _serialize_value(old_val) == _serialize_value(new_val):
            continue
        db.add(
            ObjectHistory(
                object_id=obj.id,
                field_name=field,
                old_value=_serialize_value(old_val),
                new_value=_serialize_value(new_val),
            )
        )
        setattr(obj, field, new_val)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_object(db: AsyncSession, obj: ConstructionObject) -> None:
    await db.delete(obj)
    await db.commit()


async def dashboard_stats(db: AsyncSession) -> dict:
    result = await db.execute(select(ConstructionObject))
    objects = list(result.scalars().all())
    today = date.today()
    by_status: dict[str, int] = {}
    for o in objects:
        key = o.status.value
        by_status[key] = by_status.get(key, 0) + 1
    total_budget = sum((o.budget_rub for o in objects), Decimal("0"))
    total_spent = sum((o.spent_rub for o in objects), Decimal("0"))
    overdue = [o for o in objects if o.is_overdue(today)]
    return {
        "by_status": by_status,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "overdue_count": len(overdue),
        "overdue_ids": [o.id for o in overdue],
        "budget_by_municipality": _budget_by_municipality(objects),
    }


def _budget_by_municipality(objects: list[ConstructionObject]) -> dict[str, float]:
    acc: dict[str, Decimal] = {}
    for o in objects:
        acc[o.municipality] = acc.get(o.municipality, Decimal("0")) + o.budget_rub
    return {k: float(v) for k, v in sorted(acc.items(), key=lambda x: -x[1])[:10]}
