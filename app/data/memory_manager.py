"""
Humanic AI – Memory Manager (ChromaDB)
Handles embedding, saving, and retrieving user memories for RAG context.
Uses GPT-4o-mini for intelligent fact extraction instead of regex heuristics.
"""

import json
import uuid
import logging
from datetime import datetime, timezone

import chromadb
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# OpenAI client (shared)
# ──────────────────────────────────────────────

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


# ──────────────────────────────────────────────
# ChromaDB client & collection (singleton-style)
# ──────────────────────────────────────────────

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "humanic_memories"


def _get_client() -> chromadb.ClientAPI:
    """Lazy-init a persistent ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        logger.info("ChromaDB client initialised (dir=%s)", settings.CHROMA_PERSIST_DIR)
    return _client


def _get_collection() -> chromadb.Collection:
    """Lazy-init the memories collection."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready", COLLECTION_NAME)
    return _collection


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def save_memory(user_id: str, text: str, metadata: dict | None = None) -> str:
    """Embed and persist a user memory.

    Returns the auto-generated document id.
    """
    collection = _get_collection()
    doc_id = str(uuid.uuid4())
    meta = {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    collection.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[meta],
    )
    logger.debug("Saved memory %s for user %s", doc_id, user_id)
    return doc_id


def retrieve_memories(user_id: str, query: str, top_k: int = 5) -> list[str]:
    """Return the most relevant stored memories for the given query.

    Filters by user_id so users never see each other's data.
    """
    collection = _get_collection()

    # Guard: if the collection is empty, skip the query
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"user_id": user_id},
    )

    documents: list[str] = []
    if results and results.get("documents"):
        documents = [doc for doc in results["documents"][0] if doc]
    return documents


# ──────────────────────────────────────────────
# Intelligent fact extraction (GPT-4o-mini)
# ──────────────────────────────────────────────

_EXTRACT_SYSTEM_PROMPT = """You are a silent background worker. Extract any new personal facts, \
preferences, relationships, or emotional states from the user's text. \
Return them as a raw JSON list of strings. If there are no new facts, \
return an empty list []. Do not include 'I' or 'User', rewrite them as \
facts like 'User likes blue'. Do not answer the user.

Examples:
  Input: "My favorite color is blue and I love painting"
  Output: ["User's favorite color is blue", "User loves painting"]

  Input: "I'm really worried about my dog, Rex, he's been sick all week."
  Output: ["User is worried about their dog Rex", "User's dog Rex has been sick all week"]

  Input: "What's the weather like?"
  Output: []
"""


def intelligent_extract(user_text: str) -> list[str]:
    """Use GPT-4o-mini to intelligently extract personal facts from user text.

    Replaces the old regex heuristic with a lightweight LLM call that
    catches nuanced facts the regex approach would miss.
    """
    if not user_text.strip():
        return []

    client = _get_openai()
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.0,
            max_tokens=300,
        )

        raw = (completion.choices[0].message.content or "[]").strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        facts = json.loads(raw)

        if isinstance(facts, list):
            return [str(f) for f in facts if f]
        return []

    except Exception:
        logger.exception("Intelligent fact extraction failed")
        return []
