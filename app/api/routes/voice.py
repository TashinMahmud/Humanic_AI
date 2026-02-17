"""
Humanic AI – Real-Time Voice WebSocket Endpoint
Streams GPT-4o responses token-by-token over WebSocket for low-latency
voice interface support. Handles both text and audio (STT) input.
Optionally pipes text through ElevenLabs TTS for real-time audio output.
Persists all messages via SQLite chat history.

Protocol:
  1. Client connects to /ws/chat/{user_id}
  2. Client sends JSON text frame:
       {"message": "...", "role": "friend", "voice_id": "...", "session_id": "..."}
     OR binary audio frame (raw webm/wav blob from MediaRecorder)
  3. For audio input, server responds with:
       {"type": "transcript", "text": "..."}
  4. Server sends CONTROL packet:  {"type": "control", "emotion": "...", "animation_trigger": "..."}
  5. Server sends STREAM packets:  {"type": "stream", "token": "..."} (one per token)
  6. Server sends AUDIO packets:   {"type": "audio", "data": "<base64>"} (if TTS enabled)
  7. Server sends END packet:      {"type": "end", "full_text": "..."}
  8. Connection stays open for next message.
"""

import base64
import json
import logging
from collections.abc import Generator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI

from app.core.config import settings
from app.data.history_manager import add_message, get_history, create_session
from app.data.memory_manager import intelligent_extract, retrieve_memories, save_memory
from app.services.ai_engine import AIResponse
from app.services.personalities import get_personality
from app.services.stt import transcribe
from app.services.tts import VOICE_OPTIONS, generate_audio

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
    """Real-time streaming chat over WebSocket with STT, TTS, and history."""
    await websocket.accept()
    logger.info("WebSocket connected: user=%s", user_id)

    # ── Session state ──
    session_id: str | None = None
    role: str = "friend"
    voice_id: str = ""
    conversation_history: list[dict[str, str]] = []
    MAX_HISTORY = 20

    try:
        while True:
            # ── Receive frame (text JSON or binary audio) ──
            ws_message = await websocket.receive()

            message_text: str = ""

            if "text" in ws_message:
                # ── JSON text frame ──
                try:
                    data = json.loads(ws_message["text"])
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                    continue

                message_text = data.get("message", "").strip()
                role = data.get("role", role)
                voice_id = data.get("voice_id", voice_id)

                # Session management
                if data.get("session_id"):
                    session_id = data["session_id"]

                # Config-only frame (no message to process)
                if data.get("type") == "config":
                    continue

            elif "bytes" in ws_message:
                # ── Binary audio frame → STT ──
                audio_bytes = ws_message["bytes"]
                if not audio_bytes:
                    continue

                logger.info("Received audio: %d bytes from user=%s", len(audio_bytes), user_id)
                message_text = transcribe(audio_bytes, file_format="webm")

                if not message_text:
                    await websocket.send_json({
                        "type": "transcript",
                        "text": "",
                        "status": "no_speech_detected",
                    })
                    continue

                # Send transcript back so client shows what was heard
                await websocket.send_json({
                    "type": "transcript",
                    "text": message_text,
                })

            # ── Create session if needed ──
            if not session_id:
                session_id = create_session()
                await websocket.send_json({
                    "type": "session",
                    "session_id": session_id,
                })

            enable_tts = bool(voice_id)

            if not message_text:
                await websocket.send_json({"type": "error", "detail": "Empty message"})
                continue

            # ── 1. Save user message to history ──
            add_message(session_id, "user", message_text)

            # ── 2. Retrieve memories ──
            memories = retrieve_memories(user_id, message_text, top_k=5)
            memory_context = ""
            if memories:
                memory_block = "\n".join(f"- {m}" for m in memories)
                memory_context = (
                    f"\n\n### Things you remember about this user:\n{memory_block}\n"
                )

            system_prompt = get_personality(role) + memory_context
            client = _get_openai()

            # Build messages with conversation history
            messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history[-MAX_HISTORY:],
                {"role": "user", "content": message_text},
            ]

            # ── 3. Quick pre-pass: get emotion + animation ──
            try:
                meta_completion = client.beta.chat.completions.parse(
                    model=settings.MODEL_NAME,
                    messages=messages,
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

            # ── 4. Send CONTROL packet ──
            await websocket.send_json({
                "type": "control",
                "emotion": emotion,
                "animation_trigger": animation,
            })

            # ── 5. Stream the reply token-by-token ──
            full_text = ""

            stream = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
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

            # ── 6. Stream TTS audio (if voice_id provided) ──
            if enable_tts and full_text.strip():
                await websocket.send_json({"type": "audio_start"})

                for audio_chunk in generate_audio(full_text, voice_id=voice_id):
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_chunk).decode("ascii"),
                    })

                await websocket.send_json({"type": "audio_end"})

            # ── 7. Send END packet ──
            await websocket.send_json({
                "type": "end",
                "full_text": full_text,
            })

            # ── 8. Save AI response to history ──
            add_message(session_id, "assistant", full_text)

            # ── 9. Update in-memory conversation context ──
            conversation_history.append({"role": "user", "content": message_text})
            conversation_history.append({"role": "assistant", "content": full_text})

            # ── 10. Background: extract and save facts ──
            facts = intelligent_extract(message_text)
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


@router.get("/voices", tags=["Voice"])
async def list_voices():
    """Return available TTS voice options for the frontend."""
    return {"voices": VOICE_OPTIONS}


@router.get("/history/{session_id}", tags=["Voice"])
async def fetch_history(session_id: str, limit: int = 20):
    """Return message history for a session."""
    messages = get_history(session_id, limit=limit)
    return {"session_id": session_id, "messages": messages}
