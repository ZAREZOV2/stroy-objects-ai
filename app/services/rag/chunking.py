"""Разбиение текста на фрагменты для индексации."""

import re


def split_text(text: str, chunk_size: int = 650, overlap: int = 80) -> list[str]:
    """Простое разбиение по абзацам с перекрытием символов."""
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                # длинный абзац режем по символам
                start = 0
                while start < len(para):
                    part = para[start : start + chunk_size]
                    chunks.append(part)
                    start += chunk_size - overlap
                current = ""
    if current:
        chunks.append(current)

    # добавляем перекрытие между соседними короткими чанками
    if overlap and len(chunks) > 1:
        merged: list[str] = []
        for i, ch in enumerate(chunks):
            if i > 0 and len(chunks[i - 1]) > overlap:
                prefix = chunks[i - 1][-overlap:]
                merged.append(f"{prefix}… {ch}")
            else:
                merged.append(ch)
        return merged
    return chunks
