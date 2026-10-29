"""Pydantic-схемы для API объектов."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.object import ObjectStatus, ObjectType


class ObjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    object_type: ObjectType
    municipality: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1, max_length=500)
    contractor: str = Field(..., min_length=1, max_length=300)
    status: ObjectStatus
    planned_start: date | None = None
    planned_end: date | None = None
    actual_end: date | None = None
    budget_rub: Decimal = Field(default=Decimal("0"), ge=0)
    spent_rub: Decimal = Field(default=Decimal("0"), ge=0)


class ObjectCreate(ObjectBase):
    pass


class ObjectUpdate(BaseModel):
    name: str | None = None
    object_type: ObjectType | None = None
    municipality: str | None = None
    address: str | None = None
    contractor: str | None = None
    status: ObjectStatus | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    actual_end: date | None = None
    budget_rub: Decimal | None = None
    spent_rub: Decimal | None = None


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime
    comment: str | None


class ObjectRead(ObjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    budget_execution_pct: float = 0.0
    history: list[HistoryRead] = []


class DashboardStats(BaseModel):
    by_status: dict[str, int]
    total_budget: Decimal
    total_spent: Decimal
    overdue_count: int
    overdue_ids: list[int]
