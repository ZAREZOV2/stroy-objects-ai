"""Модели учёта строительных объектов."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ObjectType(str, enum.Enum):
    school = "школа"
    kindergarten = "детсад"
    road = "дорога"
    hospital = "больница"
    other = "прочее"


class ObjectStatus(str, enum.Enum):
    design = "проектирование"
    construction = "строительство"
    paused = "приостановлен"
    completed = "сдан"


class ConstructionObject(Base):
    __tablename__ = "construction_objects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    object_type: Mapped[ObjectType] = mapped_column(
        Enum(ObjectType, name="object_type_enum", native_enum=False, length=50),
        nullable=False,
    )
    municipality: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    contractor: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[ObjectStatus] = mapped_column(
        Enum(ObjectStatus, name="object_status_enum", native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget_rub: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    spent_rub: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["ObjectHistory"]] = relationship(
        back_populates="object",
        cascade="all, delete-orphan",
        order_by="ObjectHistory.changed_at.desc()",
    )

    def is_overdue(self, today: date | None = None) -> bool:
        """Объект просрочен, если срок окончания прошёл и статус не «сдан»."""
        ref = today or date.today()
        if self.status == ObjectStatus.completed:
            return False
        if self.planned_end and self.planned_end < ref:
            return True
        return False

    @property
    def budget_execution_pct(self) -> float:
        if self.budget_rub and self.budget_rub > 0:
            return float(self.spent_rub / self.budget_rub * 100)
        return 0.0


class ObjectHistory(Base):
    __tablename__ = "object_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("construction_objects.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    object: Mapped[ConstructionObject] = relationship(back_populates="history")
