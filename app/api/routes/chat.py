"""
Humanic AI – Chat Route
POST /chat endpoint that ties together moderation, memory, and AI engine.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse, ModerationBlock
from app.services.ai_engine import generate_response
from app.utils.moderation import enforce_moderation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a message to the AI companion",
    responses={
        451: {
            "model": ModerationBlock,
            "description": "Message blocked by safety moderation.",
        }
    },
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint.

    Flow:
    1. Moderate the incoming message (raises 451 if unsafe).
    2. Generate an AI response (memory retrieval + LLM + fact saving).
    3. Return structured ChatResponse with emotion & animation metadata.
    """
    # Step 1 – Safety gate
    enforce_moderation(request.message)

    # Step 2 – AI response generation
    try:
        response = generate_response(
            user_id=request.user_id,
            message=request.message,
            role=request.role,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.exception("AI engine error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return response
