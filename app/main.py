"""
Humanic AI – FastAPI Entrypoint
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.voice import router as voice_router
from app.core.config import settings
from app.services.personalities import list_roles

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=(
        "The **Emotional Brain** behind Humanic — an AI companion with "
        "multi-role personalities, long-term vector memory, real-time "
        "emotion & animation metadata, and built-in safety moderation."
    ),
)

# ── CORS (permissive for dev; tighten in production) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(chat_router, prefix="/api/v1")
app.include_router(voice_router)


# ── Health check ──
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "model": settings.MODEL_NAME,
        "available_roles": list_roles(),
    }
