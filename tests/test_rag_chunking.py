from app.models.document import DocumentChunk
from app.services.rag.chunking import split_text
from app.services.rag.search import keyword_search


def test_split_text_produces_chunks():
    text = "Абзац один.\n\n" + "Абзац два с текстом. " * 50
    chunks = split_text(text, chunk_size=200, overlap=30)
    assert len(chunks) >= 2
    assert all(len(c) <= 250 for c in chunks)


def test_keyword_search_ranks_relevant_chunk():
    chunks = [
        DocumentChunk(id=1, document_id=1, chunk_index=0, content="Порядок приёмки объекта заказчиком"),
        DocumentChunk(id=2, document_id=1, chunk_index=1, content="Погода в горах Урала"),
    ]
    hits = keyword_search(chunks, "приёмка объекта заказчик", top_k=1)
    assert hits
    assert hits[0][0].chunk_index == 0
    assert hits[0][1] > 0
