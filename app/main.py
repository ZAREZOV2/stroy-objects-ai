"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.objects import router as objects_api
from app.api.rag import router as rag_api
from app.config import get_settings
from app.web.routes import router as web_router

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.samples_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Портал учёта строительных объектов",
    description=(
        "Демонстрационный внутренний сервис: реестр объектов и ИИ-помощник "
        "по нормативным документам (Свердловская область, вымышленные данные)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(objects_api)
app.include_router(rag_api)
