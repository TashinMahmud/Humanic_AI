"""
Humanic AI – Speech-to-Text Service (OpenAI Whisper)
Converts audio bytes to text using the Whisper API.
"""

import io
import logging

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def transcribe(audio_bytes: bytes, file_format: str = "webm") -> str:
    """Transcribe audio bytes to text using OpenAI Whisper.

    Args:
        audio_bytes: Raw audio data from the browser's MediaRecorder.
        file_format: Audio format (webm, wav, mp3, etc.).

    Returns:
        Transcribed text string.
    """
    client = _get_openai()

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"recording.{file_format}"

    try:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
        )
        text = result.strip() if isinstance(result, str) else str(result).strip()
        logger.info("Whisper transcribed %d bytes → '%s'", len(audio_bytes), text[:80])
        return text
    except Exception:
        logger.exception("Whisper transcription failed")
        return ""
