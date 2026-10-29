# Развёртывание на Linux VDS (CPU, без GPU)

Инструкция для виртуального сервера с Docker: приложение, PostgreSQL и **локальные** модели Ollama за nginx с HTTPS.

**Целевой профиль:** 4 vCPU, **~7 ГБ свободной RAM**, без GPU.

## Требования к серверу

| Компонент | Ориентир по RAM |
|-----------|-----------------|
| PostgreSQL (pgvector) | 512 МБ – 1 ГБ |
| FastAPI-приложение | 256 – 512 МБ |
| Ollama + **Spark-X2.5-1.7B** (Q4, по умолчанию) | ~1,5 – 2,5 ГБ |
| Ollama + **bge-m3** (эмбеддинги) | ~600 МБ – 1 ГБ |
| ОС, nginx, запас | ~512 МБ – 1 ГБ |

На **~7 ГБ свободной RAM** и **4 CPU** комфортно работает связка **1.7B + bge-m3** при `OLLAMA_NUM_CTX=1536` (значение по умолчанию).

**Более тяжёлый чат (опционально):** `OLLAMA_CHAT_MODEL=SparkLLM/Spark-X2.5-4B` — лучше качество ответов, но +1–2 ГБ RAM; при OOM верните 1.7B или уменьшите `OLLAMA_NUM_CTX` до `1280`.

Ollama держит **одну** загруженную модель (`OLLAMA_MAX_LOADED_MODELS=1`); чат и эмбеддинги подгружаются по очереди.

## Модели

| Назначение | Переменная | Значение по умолчанию | Зачем |
|------------|------------|----------------------|--------|
| Чат (RAG) | `OLLAMA_CHAT_MODEL` | `SparkLLM/Spark-X2.5-1.7B` | CPU-friendly; **Ollama ≥ 0.34.1** (`ollama/ollama:0.34.1`) |
| Чат (тяжелее) | `OLLAMA_CHAT_MODEL` | `SparkLLM/Spark-X2.5-4B` | Опционально через `.env` |
| Эмбеддинги | `OLLAMA_EMBED_MODEL` | `bge-m3` | Мультиязычная, **русский** |
| Размерность | `OLLAMA_EMBED_DIMENSIONS` | `1024` | Совпадает с pgvector |
| Контекст LLM | `OLLAMA_NUM_CTX` | `1536` | Умеренное окно под 7 ГБ RAM |

## 1. Подготовка сервера

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
git clone <URL-репозитория> stroy-portal && cd stroy-portal
cp .env.example .env
```

## 2. Запуск с Ollama

```bash
docker compose --profile ollama up -d --build
```

### Загрузка моделей

```bash
docker compose exec ollama ollama pull bge-m3
docker compose exec ollama ollama pull SparkLLM/Spark-X2.5-1.7B
# опционально:
# docker compose exec ollama ollama pull SparkLLM/Spark-X2.5-4B
```

Проверка: `docker compose exec ollama ollama list`

## 3. nginx + HTTPS (Let's Encrypt)

```nginx
server {
    listen 80;
    server_name portal.example.gov.local;
    return 301 https://$host$request_uri;
}

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

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d portal.example.gov.local
```

Production: `DEBUG=false`, смените пароли БД.

## 4. Лимиты памяти

```env
OLLAMA_NUM_CTX=1536
RAG_MAX_CONTEXT_CHARS=4500
RAG_MAX_CHUNK_CHARS_FOR_EMBED=1500
OLLAMA_CHAT_MODEL=SparkLLM/Spark-X2.5-1.7B
```

Без Ollama сервис стартует; `/assistant` — BM25-fallback.

## 5. Бэкапы

```bash
docker compose exec db pg_dump -U stroy stroy_db > backup.sql
```

Тома: `pgdata`, `ollama_data`, `data/uploads`.
