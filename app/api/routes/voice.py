"""
Humanic AI – Real-Time Voice WebSocket Endpoint
Streams GPT-4o responses token-by-token over WebSocket for low-latency
voice interface support.

Protocol:
  1. Client connects to /ws/chat/{user_id}
  2. Client sends JSON text frame: {"message": "...", "role": "friend"}
  3. Server sends CONTROL packet:  {"type": "control", "emotion": "...", "animation_trigger": "..."}
  4. Server sends STREAM packets:  {"type": "stream", "token": "..."} (one per token)
  5. Server sends END packet:      {"type": "end", "full_text": "..."}
  6. Connection stays open for next message.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI

from app.core.config import settings
from app.data.memory_manager import intelligent_extract, retrieve_memories, save_memory
from app.services.ai_engine import AIResponse
from app.services.personalities import get_personality

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


@router.websocket("/ws/chat/{user_id}")
async def voice_chat(websocket: WebSocket, user_id: str):
    """Real-time streaming chat over WebSocket.

    Accepts a connection, then loops:
      - receives a JSON text frame with {message, role}
      - sends a control packet with emotion/animation (from a fast structured-output pre-pass)
      - streams GPT-4o tokens one-by-one
      - sends an end packet with the full assembled text
    """
    await websocket.accept()
    logger.info("WebSocket connected: user=%s", user_id)

    try:
        while True:
            # ── Receive message ──
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            message = data.get("message", "").strip()
            role = data.get("role", "friend")

            if not message:
                await websocket.send_json({"type": "error", "detail": "Empty message"})
                continue

            # ── 1. Retrieve memories ──
            memories = retrieve_memories(user_id, message, top_k=5)
            memory_context = ""
            if memories:
                memory_block = "\n".join(f"- {m}" for m in memories)
                memory_context = (
                    f"\n\n### Things you remember about this user:\n{memory_block}\n"
                )

            system_prompt = get_personality(role) + memory_context
            client = _get_openai()

            # ── 2. Quick pre-pass: get emotion + animation via structured output ──
            try:
                meta_completion = client.beta.chat.completions.parse(
                    model=settings.MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    response_format=AIResponse,
                    temperature=0.85,
                )
                ai_meta: AIResponse = meta_completion.choices[0].message.parsed  # type: ignore
                emotion = ai_meta.emotion.value
                animation = ai_meta.animation_trigger.value
            except Exception:
                logger.exception("Structured pre-pass failed, using defaults")
                emotion = "Neutral"
                animation = "NOD_COMPASSION"

            # ── 3. Send CONTROL packet immediately ──
            await websocket.send_json({
                "type": "control",
                "emotion": emotion,
                "animation_trigger": animation,
            })

            # ── 4. Stream the actual reply token-by-token ──
            full_text = ""
            stream = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.85,
                max_tokens=800,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    token = delta.content
                    full_text += token
                    await websocket.send_json({
                        "type": "stream",
                        "token": token,
                    })

            # ── 5. Send END packet ──
            await websocket.send_json({
                "type": "end",
                "full_text": full_text,
            })

            # ── 6. Background: extract and save facts ──
            facts = intelligent_extract(message)
            for fact in facts:
                save_memory(user_id, fact, metadata={"source": "voice", "role": role})
                logger.info("Saved fact for %s: %s", user_id, fact[:60])

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user=%s", user_id)
    except Exception:
        logger.exception("WebSocket error for user=%s", user_id)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except RuntimeError:
            pass
