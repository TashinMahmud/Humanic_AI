"""
Humanic AI – Chat Schemas
Pydantic models for the /chat request and response.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from the client."""

    user_id: str = Field(
        ...,
        description="Unique identifier for the user (from your auth system).",
        examples=["user_abc123"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's message text.",
        examples=["How can I be more productive?"],
    )
    role: str = Field(
        default="friend",
        description="Personality role the AI should adopt.",
        examples=["mentor", "friend", "flirt", "therapist", "spiritual", "partner"],
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to group a conversation thread.",
    )


class ChatResponse(BaseModel):
    """Structured response returned by the AI engine."""

    text: str = Field(
        ...,
        description="The AI companion's reply.",
    )
    emotion: str = Field(
        ...,
        description="Detected emotional sentiment of the reply.",
        examples=["Happy", "Sad", "Anxious", "Calm", "Neutral"],
    )
    animation_trigger: str = Field(
        ...,
        description="Animation code for the 3D avatar.",
        examples=["NOD_COMPASSION", "SMILE_WARM", "LEAN_FORWARD"],
    )
    audio_url: str | None = Field(
        default=None,
        description="Placeholder URL for future TTS audio (ElevenLabs).",
    )
    session_id: str = Field(
        ...,
        description="Session identifier for this conversation thread.",
    )


class ModerationBlock(BaseModel):
    """Returned when the moderation layer flags a message."""

    blocked: bool = True
    reason: str = Field(
        ..., description="Human-readable reason for blocking."
    )
    flagged_categories: list[str] = Field(
        default_factory=list,
        description="OpenAI moderation categories that were triggered.",
    )
