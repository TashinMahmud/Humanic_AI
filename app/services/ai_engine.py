"""
Humanic AI – AI Engine (Native AI Architecture)
Uses OpenAI Structured Outputs for reliable emotion/animation metadata.
"""

import logging
import uuid
from enum import Enum
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.data.memory_manager import intelligent_extract, retrieve_memories, save_memory
from app.schemas.chat import ChatResponse
from app.services.personalities import get_personality

logger = logging.getLogger(__name__)

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


# ──────────────────────────────────────────────
# Structured Output schema
# ──────────────────────────────────────────────


class EmotionType(str, Enum):
    HAPPY = "Happy"
    SAD = "Sad"
    ANXIOUS = "Anxious"
    EXCITED = "Excited"
    CALM = "Calm"
    ANGRY = "Angry"
    TENDER = "Tender"
    CURIOUS = "Curious"
    PLAYFUL = "Playful"
    NEUTRAL = "Neutral"


class AnimationTrigger(str, Enum):
    NOD_COMPASSION = "NOD_COMPASSION"
    SMILE_WARM = "SMILE_WARM"
    LEAN_FORWARD = "LEAN_FORWARD"
    WAVE_HELLO = "WAVE_HELLO"
    HEAD_TILT_CURIOUS = "HEAD_TILT_CURIOUS"
    LAUGH_GENTLE = "LAUGH_GENTLE"
    HUG_VIRTUAL = "HUG_VIRTUAL"
    SIGH_EMPATHY = "SIGH_EMPATHY"
    CELEBRATE = "CELEBRATE"
    THINK_DEEP = "THINK_DEEP"
    LISTEN_INTENT = "LISTEN_INTENT"
    COMFORT_PAT = "COMFORT_PAT"
    EYEBROW_RAISE = "EYEBROW_RAISE"
    WINK_PLAYFUL = "WINK_PLAYFUL"
    HAND_HEART = "HAND_HEART"
    BREATHE_CALM = "BREATHE_CALM"
    POINT_ENCOURAGE = "POINT_ENCOURAGE"
    SHRUG_CASUAL = "SHRUG_CASUAL"
    FIST_BUMP = "FIST_BUMP"
    TEAR_WIPE = "TEAR_WIPE"


class AIResponse(BaseModel):
    """Schema enforced via OpenAI Structured Outputs.

    The model fills every field — no regex parsing needed.
    """

    reply_text: str = Field(
        description="The AI companion's conversational reply to the user."
    )
    emotion: EmotionType = Field(
        description="The dominant emotion expressed in the reply."
    )
    animation_trigger: AnimationTrigger = Field(
        description="The 3D avatar animation that best matches the reply's tone."
    )


# ──────────────────────────────────────────────
# Main chat completion
# ──────────────────────────────────────────────


def generate_response(
    user_id: str,
    message: str,
    role: str = "friend",
    session_id: str | None = None,
) -> ChatResponse:
    """Full orchestration: memory retrieval → LLM call → fact saving → response.

    Uses OpenAI Structured Outputs (beta.chat.completions.parse) so the
    model returns a validated AIResponse — no regex, no JSON scraping.
    """
    session_id = session_id or str(uuid.uuid4())

    # 1. Retrieve relevant memories
    memories = retrieve_memories(user_id, message, top_k=5)
    memory_context = ""
    if memories:
        memory_block = "\n".join(f"- {m}" for m in memories)
        memory_context = (
            f"\n\n### Things you remember about this user:\n{memory_block}\n"
        )

    # 2. Build system prompt
    system_prompt = get_personality(role) + memory_context

    # 3. Call OpenAI with Structured Outputs
    client = _get_openai()
    completion = client.beta.chat.completions.parse(
        model=settings.MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        response_format=AIResponse,
        temperature=0.85,
    )

    ai_response: AIResponse = completion.choices[0].message.parsed  # type: ignore[assignment]

    # 4. Intelligent fact extraction & saving (via gpt-4o-mini)
    facts = intelligent_extract(message)
    for fact in facts:
        save_memory(user_id, fact, metadata={"source": "user_message", "role": role})
        logger.info("Saved fact for %s: %s", user_id, fact[:60])

    # 5. Build response
    return ChatResponse(
        text=ai_response.reply_text,
        emotion=ai_response.emotion.value,
        animation_trigger=ai_response.animation_trigger.value,
        audio_url=None,  # Placeholder for future ElevenLabs integration
        session_id=session_id,
    )
