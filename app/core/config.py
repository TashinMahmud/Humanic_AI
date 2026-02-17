"""
Humanic AI – Application Configuration
Loads environment variables via pydantic-settings and python-dotenv.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to project root (two levels up from this file)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenAI ──
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o"

    # ── ChromaDB ──
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # ── Chat History ──
    CHAT_DB_DIR: str = "./chat_data"

    # ── ElevenLabs TTS ──
    ELEVEN_API_KEY: str = ""
    ELEVEN_VOICE_ID: str = "JBFqnCBsd6RMkjVDRZzb"  # "George" default
    ELEVEN_MODEL_ID: str = "eleven_multilingual_v2"

    # ── Server ──
    APP_TITLE: str = "Humanic AI – Emotional Brain"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False


settings = Settings()
