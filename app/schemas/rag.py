"""Pydantic-схемы для RAG API."""

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    file_type: str
    is_demo: bool
    chunk_count: int = 0


class Citation(BaseModel):
    document_id: int
    document_title: str
    chunk_index: int
    excerpt: str
    score: float | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    mode: str  # "llm" | "keyword" | "objects"
    citations: list[Citation] = []
    ollama_available: bool
    note: str | None = None
