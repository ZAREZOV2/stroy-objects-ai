"""HTTP-клиент для Ollama (чат и эмбеддинги) с ограничениями под CPU/VDS."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


async def check_ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    if not texts:
        return []
    max_len = settings.rag_max_chunk_chars_for_embed
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            vectors: list[list[float]] = []
            for text in texts:
                prompt = truncate_text(text, max_len)
                r = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": prompt},
                )
                if r.status_code != 200:
                    logger.warning("Ollama embeddings HTTP %s", r.status_code)
                    return None
                vec = r.json()["embedding"]
                if len(vec) != settings.ollama_embed_dimensions:
                    logger.warning(
                        "Размерность эмбеддинга %s != OLLAMA_EMBED_DIMENSIONS=%s",
                        len(vec),
                        settings.ollama_embed_dimensions,
                    )
                vectors.append(vec)
            return vectors
    except httpx.HTTPError as exc:
        logger.warning("Ollama embeddings error: %s", exc)
        return None


async def chat(system: str, user: str, context: str) -> str | None:
    context = truncate_text(context, settings.rag_max_context_chars)
    prompt = (
        f"{system}\n\nКонтекст из нормативных документов:\n{context}\n\n"
        f"Вопрос пользователя: {user}\n\n"
        "Ответь кратко по-русски, опираясь только на контекст. "
        "Укажи, из какого фрагмента взята информация."
    )
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_chat_model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "options": {
                        "num_ctx": settings.ollama_num_ctx,
                        "num_predict": 512,
                    },
                },
            )
            if r.status_code != 200:
                logger.warning("Ollama generate HTTP %s: %s", r.status_code, r.text[:200])
                return None
            return r.json().get("response", "").strip()
    except httpx.HTTPError:
        return None
