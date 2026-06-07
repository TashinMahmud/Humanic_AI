"""
Humanic AI – AI Engine (Native AI Architecture)
Uses OpenAI Structured Outputs for reliable emotion/animation metadata.
"""

import logging
import uuid
import json
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
        if settings.GROQ_API_KEY:
            _openai_client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        else:
            if not settings.OPENAI_API_KEY:
                raise ValueError("Neither OPENAI_API_KEY nor GROQ_API_KEY is set in environment.")
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
# Session-based conversation history (in-memory)
# ──────────────────────────────────────────────

_session_histories: dict[str, list[dict[str, str]]] = {}
MAX_HISTORY = 20  # Keep last N messages per session


def generate_response(
    user_id: str,
    message: str,
    role: str = "friend",
    session_id: str | None = None,
) -> ChatResponse:
    """Full orchestration: memory retrieval → LLM call → fact saving → response.

    Uses OpenAI Structured Outputs (beta.chat.completions.parse) so the
    model returns a validated AIResponse — no regex, no JSON scraping.
    Maintains conversation history per session_id for multi-turn context.
    """
    session_id = session_id or str(uuid.uuid4())

    # Get or create session history
    if session_id not in _session_histories:
        _session_histories[session_id] = []
    history = _session_histories[session_id]

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

    # 3. Build messages with conversation history
    messages = [
        {"role": "system", "content": system_prompt},
        *history[-MAX_HISTORY:],
        {"role": "user", "content": message},
    ]

    # 4. Call OpenAI/Groq for response
    client = _get_openai()
    if settings.GROQ_API_KEY:
        schema_instruction = """
        You must return a valid JSON object matching this schema:
        {
          "reply_text": "string (conversational reply to the user)",
          "emotion": "Happy" | "Sad" | "Anxious" | "Excited" | "Calm" | "Angry" | "Tender" | "Curious" | "Playful" | "Neutral",
          "animation_trigger": "NOD_COMPASSION" | "SMILE_WARM" | "LEAN_FORWARD" | "WAVE_HELLO" | "HEAD_TILT_CURIOUS" | "LAUGH_GENTLE" | "HUG_VIRTUAL" | "SIGH_EMPATHY" | "CELEBRATE" | "THINK_DEEP" | "LISTEN_INTENT" | "COMFORT_PAT" | "EYEBROW_RAISE" | "WINK_PLAYFUL" | "HAND_HEART" | "BREATHE_CALM" | "POINT_ENCOURAGE" | "SHRUG_CASUAL" | "FIST_BUMP" | "TEAR_WIPE"
        }
        Return ONLY valid JSON. Do not include markdown formatting or extra text outside the JSON.
        """
        messages_with_schema = list(messages)
        messages_with_schema[0] = {
            "role": "system",
            "content": messages[0]["content"] + "\n\n" + schema_instruction
        }
        
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            messages=messages_with_schema,
            response_format={"type": "json_object"},
            temperature=0.85,
        )
        content = (completion.choices[0].message.content or "{}").strip()
        parsed_json = json.loads(content)
        
        # Safe enum values lookup
        emotion_val = parsed_json.get("emotion", "Neutral")
        if emotion_val not in [e.value for e in EmotionType]:
            emotion_val = "Neutral"
            
        anim_val = parsed_json.get("animation_trigger", "LISTEN_INTENT")
        if anim_val not in [a.value for a in AnimationTrigger]:
            anim_val = "LISTEN_INTENT"

        ai_response = AIResponse(
            reply_text=parsed_json.get("reply_text", "Hmm, let me think about that."),
            emotion=EmotionType(emotion_val),
            animation_trigger=AnimationTrigger(anim_val)
        )
    else:
        completion = client.beta.chat.completions.parse(
            model=settings.MODEL_NAME,
            messages=messages,
            response_format=AIResponse,
            temperature=0.85,
        )
        ai_response = completion.choices[0].message.parsed  # type: ignore[assignment]

    # 5. Update conversation history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_response.reply_text})

    # 6. Intelligent fact extraction & saving (via gpt-4o-mini)
    facts = intelligent_extract(message)
    for fact in facts:
        save_memory(user_id, fact, metadata={"source": "user_message", "role": role})
        logger.info("Saved fact for %s: %s", user_id, fact[:60])

    # 7. Build response
    return ChatResponse(
        text=ai_response.reply_text,
        emotion=ai_response.emotion.value,
        animation_trigger=ai_response.animation_trigger.value,
        audio_url=None,  # Placeholder for future ElevenLabs integration
        session_id=session_id,
    )

