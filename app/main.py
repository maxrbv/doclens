from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.middleware import RequestIdMiddleware
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.logging import setup_logging

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_engine().dispose()


app = FastAPI(
    title="Semantic Document Search & QA",
    debug=settings.app_env == "local",
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)
app.include_router(health_router)
