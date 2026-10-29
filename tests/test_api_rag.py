import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_status(client: AsyncClient):
    r = await client.get("/api/rag/status")
    assert r.status_code == 200
    assert "ollama_available" in r.json()


@pytest.mark.asyncio
async def test_ask_without_documents(client: AsyncClient):
    r = await client.post("/api/rag/ask", json={"question": "Какие сроки приёмки?"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert body["mode"] in ("keyword", "llm", "vector", "objects")
