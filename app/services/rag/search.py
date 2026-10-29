"""Поиск по фрагментам: векторный (pgvector) и ключевой (BM25-подобный)."""

import math
import re
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import DocumentChunk
from app.services.rag import ollama as ollama_service

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+", re.UNICODE)


def tokenize(s: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(s)]


def keyword_search(
    chunks: list[DocumentChunk], query: str, top_k: int = 5
) -> list[tuple[DocumentChunk, float]]:
    """Лёгкий BM25-подобный скоринг без внешних зависимостей."""
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    doc_freq: Counter[str] = Counter()
    tf_list: list[Counter[str]] = []
    for ch in chunks:
        tokens = tokenize(ch.content)
        tf = Counter(tokens)
        tf_list.append(tf)
        for t in set(tokens):
            doc_freq[t] += 1
    n_docs = len(chunks)
    k1, b = 1.5, 0.75
    avg_len = sum(sum(tf.values()) for tf in tf_list) / max(n_docs, 1)
    scores: list[tuple[DocumentChunk, float]] = []
    for ch, tf in zip(chunks, tf_list, strict=True):
        dl = sum(tf.values()) or 1
        score = 0.0
        for qt in q_tokens:
            idf = math.log(1 + (n_docs - doc_freq.get(qt, 0) + 0.5) / (doc_freq.get(qt, 0) + 0.5))
            freq = tf.get(qt, 0)
            score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avg_len))
        if score > 0:
            scores.append((ch, score))
    scores.sort(key=lambda x: -x[1])
    return scores[:top_k]


async def load_all_chunks(db: AsyncSession) -> list[DocumentChunk]:
    q = select(DocumentChunk).options(selectinload(DocumentChunk.document))
    result = await db.execute(q)
    return list(result.scalars().all())


async def vector_search(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[tuple[DocumentChunk, float]] | None:
    vectors = await ollama_service.embed_texts([query])
    if not vectors:
        return None
    vec = vectors[0]
    # pgvector: cosine distance — меньше = ближе; переводим в similarity
    sql = text(
        """
        SELECT dc.id, 1 - (dc.embedding <=> :vec) AS score
        FROM document_chunks dc
        WHERE dc.embedding IS NOT NULL
        ORDER BY dc.embedding <=> :vec
        LIMIT :limit
        """
    )
    result = await db.execute(sql, {"vec": str(vec), "limit": top_k})
    rows = result.all()
    if not rows:
        return []
    ids = [r[0] for r in rows]
    scores_map = {r[0]: float(r[1]) for r in rows}
    q = (
        select(DocumentChunk)
        .where(DocumentChunk.id.in_(ids))
        .options(selectinload(DocumentChunk.document))
    )
    chunks = list((await db.execute(q)).scalars().all())
    chunks.sort(key=lambda c: -scores_map.get(c.id, 0))
    return [(c, scores_map.get(c.id, 0.0)) for c in chunks]


async def hybrid_search(
    db: AsyncSession, query: str, top_k: int = 5
) -> tuple[list[tuple[DocumentChunk, float]], str]:
    """Сначала векторный поиск; при недоступности Ollama — ключевой."""
    vector_hits = await vector_search(db, query, top_k=top_k)
    if vector_hits is not None:
        return vector_hits, "vector"
    all_chunks = await load_all_chunks(db)
    return keyword_search(all_chunks, query, top_k=top_k), "keyword"
