"""Настройки приложения из переменных окружения."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://stroy:stroy@localhost:5432/stroy_db"
    database_url_sync: str = "postgresql://stroy:stroy@localhost:5432/stroy_db"

    ollama_base_url: str = "http://localhost:11434"
    # Чат по умолчанию — лёгкая модель для CPU-VDS; тяжелее: SparkLLM/Spark-X2.5-4B через env
    ollama_chat_model: str = "SparkLLM/Spark-X2.5-1.7B"
    # Эмбеддинги: bge-m3 — мультиязычная модель с хорошей поддержкой русского, ~600 МБ в Ollama
    ollama_embed_model: str = "bge-m3"
    ollama_embed_dimensions: int = 1024
    # Окно контекста LLM: умеренное значение под VDS ~7 ГБ RAM без GPU (4B + bge-m3)
    ollama_num_ctx: int = 1536
    rag_max_context_chars: int = 2000
    rag_max_chunk_chars_for_embed: int = 1500

    app_secret_key: str = "dev-secret"
    debug: bool = True

    upload_dir: str = "data/uploads"
    samples_dir: str = "data/samples"


@lru_cache
def get_settings() -> Settings:
    return Settings()
