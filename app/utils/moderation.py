"""
Humanic AI – Content Moderation
Wraps the OpenAI Moderation API to flag unsafe content.
"""

import logging

from fastapi import HTTPException
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def check_moderation(text: str) -> tuple[bool, list[str]]:
    """Run text through the OpenAI Moderation endpoint.

    Returns:
        (is_flagged, flagged_category_names)
    """
    if not settings.OPENAI_API_KEY:
        logger.debug("OPENAI_API_KEY is not configured – bypassing safety moderation check")
        return False, []

    client = _get_openai()
    try:
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
    except Exception:
        logger.exception("Moderation API call failed – allowing message through")
        return False, []

    result = response.results[0]
    if not result.flagged:
        return False, []

    # Collect whichever categories were flagged
    flagged: list[str] = []
    categories = result.categories
    for category_name in [
        "harassment",
        "harassment/threatening",
        "hate",
        "hate/threatening",
        "self-harm",
        "self-harm/instructions",
        "self-harm/intent",
        "sexual",
        "sexual/minors",
        "violence",
        "violence/graphic",
    ]:
        # category attribute names use underscores in the SDK
        attr = category_name.replace("/", "_").replace("-", "_")
        if getattr(categories, attr, False):
            flagged.append(category_name)

    logger.warning("Moderation flagged: %s", flagged)
    return True, flagged


def enforce_moderation(text: str) -> None:
    """Raise HTTP 451 if the message is flagged.

    Call this at the top of any endpoint that accepts user text.
    """
    is_flagged, categories = check_moderation(text)
    if is_flagged:
        raise HTTPException(
            status_code=451,
            detail={
                "blocked": True,
                "reason": (
                    "Your message was flagged by our safety system. "
                    "If you are in crisis, please contact a local helpline or "
                    "text HOME to 741741 (Crisis Text Line)."
                ),
                "flagged_categories": categories,
            },
        )
