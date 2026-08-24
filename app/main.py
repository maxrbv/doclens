from fastapi import FastAPI

from app.api.middleware import RequestIdMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging()

app = FastAPI(
    title="Semantic Document Search & QA",
    debug=settings.app_env == "local",
)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
