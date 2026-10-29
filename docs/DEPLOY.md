# Развёртывание на Linux VDS (CPU, без GPU)

Инструкция для виртуального сервера с Docker: приложение, PostgreSQL и **локальные** модели Ollama за nginx с HTTPS.

**Целевой профиль:** 4 vCPU, **~7 ГБ свободной RAM**, без GPU.

## Требования к серверу

| Компонент | Ориентир по RAM / диск |
|-----------|-------------------------|
| PostgreSQL (pgvector) | 512 МБ – 1 ГБ RAM |
| FastAPI-приложение | 256 – 512 МБ RAM |
| Ollama + **Spark-X2.5-1.7B** | ~1,5 – 2,5 ГБ RAM; **~3,4 ГБ на диске** после `ollama pull` |
| Ollama + **bge-m3** | ~600 МБ – 1 ГБ RAM |
| ОС, nginx, запас | ~512 МБ – 1 ГБ RAM |

На **~7 ГБ свободной RAM** и **4 CPU** комфортно работает **1.7B + bge-m3** при `OLLAMA_NUM_CTX=1536` и `RAG_MAX_CONTEXT_CHARS=2000` (контекст RAG не должен занимать всё окно — иначе модель обрежет ответ).

**Производительность (ориентир на 4 vCPU, без GPU):** один RAG-ответ с генерацией Spark-X2.5-1.7B — **~45–55 с** (поиск + embed + generate). В nginx обязательно `proxy_read_timeout 300s;`.

**Более тяжёлый чат (опционально):** `OLLAMA_CHAT_MODEL=SparkLLM/Spark-X2.5-4B` — лучше качество, но больше RAM и дольше ответ.

Ollama: **одна** загруженная модель (`OLLAMA_MAX_LOADED_MODELS=1`).

## Модели

| Назначение | Переменная | По умолчанию |
|------------|------------|--------------|
| Чат | `OLLAMA_CHAT_MODEL` | `SparkLLM/Spark-X2.5-1.7B` (Ollama ≥ **0.34.1**, `think: false` в API) |
| Эмбеддинги | `OLLAMA_EMBED_MODEL` | `bge-m3` |
| Контекст LLM | `OLLAMA_NUM_CTX` | `1536` |
| Текст RAG в промпт | `RAG_MAX_CONTEXT_CHARS` | `2000` |

## 1. Подготовка

```bash
cp .env.example .env
# задайте POSTGRES_PASSWORD и APP_SECRET_KEY
```

Порты в `docker-compose.yml` привязаны к **127.0.0.1** (доступ снаружи только через nginx).

## 2. Запуск

```bash
docker compose --profile ollama up -d --build
docker compose exec ollama ollama pull bge-m3
docker compose exec ollama ollama pull SparkLLM/Spark-X2.5-1.7B
```

## 3. nginx + HTTPS

```nginx
server {
    listen 443 ssl http2;
    server_name portal.example.gov.local;
    ssl_certificate     /etc/letsencrypt/live/portal.example.gov.local/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.example.gov.local/privkey.pem;
    client_max_body_size 25M;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

Без увеличенного `proxy_read_timeout` длинные ответы LLM обрываются по таймауту nginx (дефолт 60 с).

## 4. Лимиты

```env
OLLAMA_NUM_CTX=1536
RAG_MAX_CONTEXT_CHARS=2000
OLLAMA_CHAT_MODEL=SparkLLM/Spark-X2.5-1.7B
POSTGRES_PASSWORD=<секрет>
```

## 5. Бэкапы

```bash
docker compose exec db pg_dump -U stroy stroy_db > backup.sql
```
