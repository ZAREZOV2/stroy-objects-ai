
import pytest
from httpx import AsyncClient

from app.models.object import ObjectStatus, ObjectType


@pytest.mark.asyncio
async def test_create_and_list_objects(client: AsyncClient):
    payload = {
        "name": "Тестовая школа №1",
        "object_type": ObjectType.school.value,
        "municipality": "г. Берёзовский",
        "address": "ул. Тестовая, 1",
        "contractor": 'ООО "Тест"',
        "status": ObjectStatus.design.value,
        "planned_start": "2025-01-01",
        "planned_end": "2026-06-01",
        "budget_rub": "100000000",
        "spent_rub": "25000000",
    }
    r = await client.post("/api/objects", json=payload)
    assert r.status_code == 201
    obj_id = r.json()["id"]

    r2 = await client.get("/api/objects", params={"municipality": "Берёзовский"})
    assert r2.status_code == 200
    assert any(item["id"] == obj_id for item in r2.json())


@pytest.mark.asyncio
async def test_overdue_filter(client: AsyncClient):
    payload = {
        "name": "Просроченный объект",
        "object_type": ObjectType.road.value,
        "municipality": "г. Екатеринбург",
        "address": "—",
        "contractor": 'ООО "Тест"',
        "status": ObjectStatus.construction.value,
        "planned_end": "2020-01-01",
        "budget_rub": "1000000",
        "spent_rub": "500000",
    }
    await client.post("/api/objects", json=payload)
    r = await client.get("/api/objects", params={"overdue": True})
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_dashboard(client: AsyncClient):
    r = await client.get("/api/objects/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "by_status" in data
    assert "overdue_count" in data
