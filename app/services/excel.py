"""Импорт и экспорт объектов в Excel/CSV."""

import io
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.object import ObjectStatus, ObjectType
from app.schemas.object import ObjectCreate
from app.services import objects as object_service

TYPE_MAP = {e.value: e for e in ObjectType}
STATUS_MAP = {e.value: e for e in ObjectStatus}

EXPORT_COLUMNS = [
    ("id", "ID"),
    ("name", "Наименование"),
    ("object_type", "Тип"),
    ("municipality", "МО"),
    ("address", "Адрес"),
    ("contractor", "Подрядчик"),
    ("status", "Статус"),
    ("planned_start", "План начало"),
    ("planned_end", "План окончание"),
    ("actual_end", "Факт окончание"),
    ("budget_rub", "Бюджет, руб."),
    ("spent_rub", "Освоено, руб."),
]


def _parse_date(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "date"):
        return val.date()
    return pd.to_datetime(val, dayfirst=True).date()


def _parse_decimal(val) -> Decimal:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return Decimal("0")
    try:
        return Decimal(str(val).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


async def import_from_dataframe(db: AsyncSession, df: pd.DataFrame) -> tuple[int, list[str]]:
    """Импорт строк; возвращает (число созданных, список ошибок)."""
    errors: list[str] = []
    created = 0
    for idx, row in df.iterrows():
        try:
            name = str(row.get("Наименование", row.get("name", ""))).strip()
            if not name or name == "nan":
                continue
            otype_raw = str(row.get("Тип", row.get("object_type", "прочее"))).strip()
            status_raw = str(row.get("Статус", row.get("status", "проектирование"))).strip()
            payload = ObjectCreate(
                name=name,
                object_type=TYPE_MAP.get(otype_raw, ObjectType.other),
                municipality=str(row.get("МО", row.get("municipality", "—"))).strip(),
                address=str(row.get("Адрес", row.get("address", "—"))).strip(),
                contractor=str(row.get("Подрядчик", row.get("contractor", "—"))).strip(),
                status=STATUS_MAP.get(status_raw, ObjectStatus.design),
                planned_start=_parse_date(row.get("План начало", row.get("planned_start"))),
                planned_end=_parse_date(row.get("План окончание", row.get("planned_end"))),
                actual_end=_parse_date(row.get("Факт окончание", row.get("actual_end"))),
                budget_rub=_parse_decimal(row.get("Бюджет, руб.", row.get("budget_rub"))),
                spent_rub=_parse_decimal(row.get("Освоено, руб.", row.get("spent_rub"))),
            )
            await object_service.create_object(db, payload)
            created += 1
        except Exception as exc:  # noqa: BLE001 — собираем ошибки по строкам для пользователя
            errors.append(f"Строка {idx + 2}: {exc}")
    return created, errors


async def import_file(db: AsyncSession, content: bytes, filename: str) -> tuple[int, list[str]]:
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    else:
        df = pd.read_excel(io.BytesIO(content))
    return await import_from_dataframe(db, df)


def objects_to_excel(objects: list) -> bytes:
    rows = []
    for o in objects:
        rows.append(
            {
                "ID": o.id,
                "Наименование": o.name,
                "Тип": o.object_type.value,
                "МО": o.municipality,
                "Адрес": o.address,
                "Подрядчик": o.contractor,
                "Статус": o.status.value,
                "План начало": o.planned_start,
                "План окончание": o.planned_end,
                "Факт окончание": o.actual_end,
                "Бюджет, руб.": float(o.budget_rub),
                "Освоено, руб.": float(o.spent_rub),
                "Просрочен": "да" if o.is_overdue() else "нет",
            }
        )
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Объекты")
    return buf.getvalue()
