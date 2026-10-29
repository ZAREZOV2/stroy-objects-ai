"""Наполнение БД демо-объектами и документами (идемпотентно)."""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.object import ConstructionObject, ObjectStatus, ObjectType
from app.schemas.object import ObjectCreate
from app.services import objects as object_service
from app.services.rag import ingest as ingest_service

MUNICIPALITIES = [
    "г. Екатеринбург",
    "г. Нижний Тагил",
    "г. Каменск-Уральский",
    "г. Первоуральск",
    "г. Серов",
    "г. Берёзовский",
    "г. Полевской",
    "г. Асбест",
    "г. Ревда",
    "г. Краснотурьинск",
    "г. Лесной",
    "Сысертский ГО",
    "Белоярский ГО",
    "Нижнесергинский ГО",
]

CONTRACTORS = [
    'ООО "УралСтройМонтаж"',
    'АО "СвердловскДорСтрой"',
    'ООО "ГорСтрой Сервис"',
    'ООО "ТагилИнвестСтрой"',
    'АО "ОблКомфортСтрой"',
]

TEMPLATES = [
    ("Школа на {n} мест", ObjectType.school),
    ("Детский сад на {n} мест", ObjectType.kindergarten),
    ("Участок дороги {name}", ObjectType.road),
    ("Поликлиника {name}", ObjectType.hospital),
    ("ФОК «{name}»", ObjectType.other),
]

STREET_NAMES = ["Ленина", "Мира", "Строителей", "Советская", "Гагарина", "8 Марта"]


def _build_objects(count: int = 30) -> list[ObjectCreate]:
    random.seed(42)
    today = date.today()
    items: list[ObjectCreate] = []
    for _ in range(count):
        tmpl, otype = random.choice(TEMPLATES)
        n = random.choice([220, 350, 550, 1100, 1500])
        name_part = random.choice(["Северный", "Южный", "Центральный", "Западный"])
        name = tmpl.format(n=n, name=name_part)
        municipality = random.choice(MUNICIPALITIES)
        status = random.choice(list(ObjectStatus))
        start = today - timedelta(days=random.randint(60, 400))
        duration = random.randint(120, 540)
        planned_end = start + timedelta(days=duration)
        actual_end = None
        if status == ObjectStatus.completed:
            actual_end = planned_end - timedelta(days=random.randint(0, 20))
        elif status == ObjectStatus.paused:
            planned_end = today - timedelta(days=random.randint(10, 90))
        budget = Decimal(random.randint(50, 800)) * Decimal("1000000")
        spent_ratio = random.uniform(0.15, 1.05 if status == ObjectStatus.completed else 0.85)
        spent = (budget * Decimal(str(round(spent_ratio, 2)))).quantize(Decimal("0.01"))
        items.append(
            ObjectCreate(
                name=name,
                object_type=otype,
                municipality=municipality,
                address=(
                    f"{municipality}, ул. {random.choice(STREET_NAMES)}, "
                    f"{random.randint(1, 120)}"
                ),
                contractor=random.choice(CONTRACTORS),
                status=status,
                planned_start=start,
                planned_end=planned_end,
                actual_end=actual_end,
                budget_rub=budget,
                spent_rub=min(spent, budget * Decimal("1.1")),
            )
        )
    return items


async def main() -> None:
    async with AsyncSessionLocal() as db:
        cnt = await db.scalar(select(func.count()).select_from(ConstructionObject))
        if not cnt:
            print("Seeding construction objects…")
            for payload in _build_objects(30):
                await object_service.create_object(db, payload)
            print("Created 30 demo objects.")
        else:
            print(f"Objects already present ({cnt}), skip.")

        docs = await ingest_service.seed_sample_documents(db)
        if docs:
            print(f"Loaded {docs} demo regulatory documents.")
        else:
            print("Demo documents already loaded or samples missing.")


if __name__ == "__main__":
    asyncio.run(main())
