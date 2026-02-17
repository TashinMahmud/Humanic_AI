# Humanic AI — Emotional Brain Backend

> **AI orchestration engine** with multi-role personalities, long-term vector memory, real-time 3D animation metadata, and built-in safety moderation.

---

## Architecture

```
┌──────────────┐        ┌───────────────────────────────────┐
│  Mobile App  │◄──────►│         Traditional Backend       │
│  (Flutter /  │  REST  │  (Auth, Payments, User Profiles)  │
│   React Native)       │                                   │
└──────────────┘        └───────────┬───────────────────────┘
                                    │  HTTP POST
                                    ▼
                        ┌───────────────────────────────────┐
                        │       Humanic AI Engine           │
                        │       (this service)              │
                        │                                   │
                        │  POST /api/v1/chat                │
                        │  GET  /health                     │
                        │                                   │
                        │  ┌─────────┐  ┌──────────────┐   │
                        │  │ChromaDB │  │ OpenAI GPT-4o│   │
                        │  │(Memory) │  │  + Moderation│   │
                        │  └─────────┘  └──────────────┘   │
                        └───────────────────────────────────┘
```

---

## Handshake Protocol

Your **traditional backend** (Node.js, Django, etc.) acts as a proxy between the mobile app and this AI engine. Here's the recommended flow:

### 1. Client → Traditional Backend
The mobile app sends the user's message along with authentication headers:

```http
POST /api/messages
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "message": "I'm feeling anxious about my interview tomorrow",
  "role": "therapist"
}
```

### 2. Traditional Backend → AI Engine
Your backend authenticates the user, then forwards the request to this service:

```http
POST http://ai-engine-host:8000/api/v1/chat
Content-Type: application/json

{
  "user_id": "usr_abc123",
  "message": "I'm feeling anxious about my interview tomorrow",
  "role": "therapist",
  "session_id": "sess_xyz789"
}
```

> **Important:** The `user_id` should be a stable, unique identifier from your auth system. The AI engine uses it to scope all memory per-user.

### 3. AI Engine Response
```json
{
  "text": "That's completely understandable — interviews can feel overwhelming...",
  "emotion": "Anxious",
  "animation_trigger": "BREATHE_CALM",
  "audio_url": null,
  "session_id": "sess_xyz789"
}
```

### 4. Traditional Backend → Client
Your backend can enrich the response (e.g., save to DB, generate TTS via ElevenLabs) before returning to the mobile app.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/chat` | `POST` | Send a message, receive structured AI response |
| `/health` | `GET` | Service health check + available roles |

### `POST /api/v1/chat`

**Request Body:**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `user_id` | `string` | ✅ | — | Unique user identifier |
| `message` | `string` | ✅ | — | User's message (1-4000 chars) |
| `role` | `string` | ❌ | `"friend"` | Personality role |
| `session_id` | `string` | ❌ | auto-generated | Conversation thread ID |

**Available Roles:** `mentor`, `friend`, `flirt`, `therapist`, `spiritual`, `partner`

**Success Response (200):**
| Field | Type | Description |
|---|---|---|
| `text` | `string` | The AI's reply |
| `emotion` | `string` | Detected sentiment |
| `animation_trigger` | `string` | 3D animation code |
| `audio_url` | `string \| null` | TTS audio URL (future) |
| `session_id` | `string` | Session identifier |

**Moderation Block (451):**
```json
{
  "detail": {
    "blocked": true,
    "reason": "Your message was flagged by our safety system...",
    "flagged_categories": ["self-harm/intent"]
  }
}
```

---

## Animation Trigger Codes

| Code | Use Case |
|---|---|
| `NOD_COMPASSION` | Empathetic acknowledgment |
| `SMILE_WARM` | Happy, positive moments |
| `LEAN_FORWARD` | Showing engagement |
| `WAVE_HELLO` | Greetings |
| `HEAD_TILT_CURIOUS` | Curious / thinking |
| `LAUGH_GENTLE` | Light humor |
| `HUG_VIRTUAL` | Comfort |
| `CELEBRATE` | Excitement, wins |
| `BREATHE_CALM` | Anxiety, calming |
| `THINK_DEEP` | Philosophical moments |
| `WINK_PLAYFUL` | Playful / flirty |
| `HAND_HEART` | Tender, loving |
| `TEAR_WIPE` | Sad, empathetic |
| `FIST_BUMP` | Casual encouragement |

---

## Quick Start

```bash
# 1. Clone & enter project
cd humanica

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
#    Edit .env and set your OPENAI_API_KEY

# 5. Run the server
uvicorn app.main:app --reload --port 8000

# 6. Open interactive docs
#    http://localhost:8000/docs

# 7. Run memory test (in another terminal)
python tests/test_memory.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| AI Model | OpenAI GPT-4o |
| Memory / RAG | ChromaDB (local vector store) |
| Safety | OpenAI Moderation API |
| Config | pydantic-settings + python-dotenv |

---

## Future Integrations

- **ElevenLabs TTS** → Populate `audio_url` in responses
- **Streaming** → SSE/WebSocket support for real-time token delivery
- **Conversation History** → Multi-turn context via session-scoped message buffers
- **User Profiles** → Persistent preference storage beyond facts
