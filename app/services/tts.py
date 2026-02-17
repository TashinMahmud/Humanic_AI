"""
Humanic AI – Text-to-Speech Service (ElevenLabs)
Converts full text responses into streaming audio using the official ElevenLabs SDK.
"""

import logging
import os
from typing import Generator

from elevenlabs.client import ElevenLabs

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Default voice options (for the frontend dropdown) ──
VOICE_OPTIONS: list[dict[str, str]] = [
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George (Male)"},
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel (Female)"},
    {"id": "29vD33N1CtxCmqQRPOHJ", "name": "Drew (Male)"},
    {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni (Male)"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella (Female)"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh (Male)"},
]

_eleven_client: ElevenLabs | None = None


def _get_eleven() -> ElevenLabs:
    """Lazy-init ElevenLabs client."""
    global _eleven_client
    if _eleven_client is None:
        api_key = os.getenv("ELEVENLABS_API_KEY") or settings.ELEVEN_API_KEY or None
        _eleven_client = ElevenLabs(api_key=api_key)
    return _eleven_client


def generate_audio(
    text: str,
    voice_id: str | None = None,
) -> Generator[bytes, None, None]:
    """Convert full text into streaming audio chunks via ElevenLabs.

    Sends the FULL text in one API call (no sentence splitting).
    This is much faster than per-sentence calls.

    Args:
        text: Complete text to convert to speech.
        voice_id: ElevenLabs voice ID. Defaults to config setting.

    Yields:
        Raw MPEG audio chunks.
    """
    voice_id = voice_id or settings.ELEVEN_VOICE_ID
    client = _get_eleven()

    logger.info("TTS: %d chars → voice %s", len(text), voice_id)
    try:
        audio_iter = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=settings.ELEVEN_MODEL_ID,
            output_format="mp3_44100_128",
        )
        for chunk in audio_iter:
            if chunk:
                yield chunk
    except Exception:
        logger.exception("TTS failed for text: %s", text[:80])
