"""Маршрутизация вопросов: реестр объектов vs RAG по документам."""

import pytest

from app.services.rag.ingest import is_registry_objects_question

PRIYOMKA_Q = (
    "За сколько дней подрядчик должен уведомить о готовности к приёмке объекта?"
)


def test_priyomka_question_is_not_registry_route():
    assert not is_registry_objects_question(PRIYOMKA_Q)


def test_overdue_list_is_registry_route():
    assert is_registry_objects_question("Какие объекты просрочены?")


@pytest.mark.asyncio
async def test_ask_priyomka_uses_rag_not_objects(client):
    r = await client.post("/api/rag/ask", json={"question": PRIYOMKA_Q})
    assert r.status_code == 200
    assert r.json()["mode"] != "objects"
