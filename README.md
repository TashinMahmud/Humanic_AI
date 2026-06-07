# 🤖 Humanic AI — Emotional Brain Companion Engine

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)](#quick-start)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--Structured-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Groq](https://img.shields.io/badge/Groq-llama--3.3-orange?style=for-the-badge)](#quick-start)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Memory-0284C7?style=for-the-badge)](#memory-architecture)

---

**Humanic AI** is the premium "Emotional Brain" microservice powering the Humanic interactive avatar system. Built with **FastAPI**, **ChromaDB**, **OpenAI Structured Outputs**, and **Groq**, it maintains session-scoped multi-turn conversation memory, automatically extracts and stores user-specific facts, conducts real-time content moderation, and returns structured speech replies along with emotion markers and 3D avatar animation triggers. When Groq is used as the provider, it automatically leverages custom JSON-schema parsing and gracefully bypasses OpenAI-only moderation checks to ensure seamless development and deployment.

</div>

---

## 🛠️ Technical Architecture

Humanic AI serves as a companion orchestration engine designed to sit behind a traditional client authentication proxy.

```
┌──────────────┐        ┌───────────────────────────────────┐
│  Mobile App  │◄──────►│         Traditional Backend       │
│  (Flutter /  │  REST  │  (Auth, Payments, User Profiles)  │
│   React Native)       │                                   │
└──────────────┘        └───────────┬───────────────────────┘
                                    │  HTTP POST /chat
                                    v
                        ┌───────────────────────────────────┐
                        │       Humanic AI Engine           │
                        │                                   │
                        │  POST /api/v1/chat                │
                        │  GET  /health                     │
                        │                                   │
                        │  ┌─────────┐  ┌──────────────┐    │
                        │  │ChromaDB │  │ OpenAI GPT-4o│    │
                        │  │(Memory) │  │  + Moderation│    │
                        │  │         │  │              │    │
                        │  └────┬────┘  └──────┬───────┘    │
                        └───────┼──────────────┼────────────┘
                                v              v
                    [ ChromaDB Vector VDB ]  [ OpenAI Structured API ]
                     - retrieve_memories()    - beta.chat.completions.parse()
                     - save_memory()          - enforce_moderation()
```

### Core Code Modules & Responsibilities

*   `app/api/` Layer:
    *   [`routes/chat.py`](app/api/routes/chat.py): Central gateway handling request parsing, safety moderation, AI engine orchestration, and HTTP responses.
    *   [`routes/voice.py`](app/api/routes/voice.py): Media routes for fetching audio segments.
*   `app/services/` Layer:
    *   [`ai_engine.py`](app/services/ai_engine.py): Main agent loop, structured outputs compiler, OpenAI client initialization, and session history management.
    *   [`personalities.py`](app/services/personalities.py): Prompts and instructions defining the companion roles (`mentor`, `friend`, `flirt`, `therapist`, `spiritual`, `partner`).
*   `app/data/` Layer:
    *   [`memory_manager.py`](app/data/memory_manager.py): ChromaDB client wrapper executing memory retrievals, embedding insertions, and fact-extraction completions.
*   `app/utils/` Layer:
    *   [`moderation.py`](app/utils/moderation.py): Integrates the OpenAI Moderation API to screen and block unsafe entries.

---

## ⚡ Core Integration Interfaces

<details>
<summary><b>🤝 Client Handshake Protocol</b></summary>

Clients route messages through a primary proxy server which appends a consistent `user_id` and `session_id`.
*   **Request (Backend → AI Engine)**:
    ```http
    POST /api/v1/chat
    Content-Type: application/json

    {
      "user_id": "usr_abc123",
      "message": "I'm feeling anxious about my interview tomorrow",
      "role": "therapist",
      "session_id": "sess_xyz789"
    }
    ```
*   **Response (AI Engine → Backend)**:
    ```json
    {
      "text": "That's completely understandable — interviews can feel overwhelming...",
      "emotion": "Anxious",
      "animation_trigger": "BREATHE_CALM",
      "audio_url": null,
      "session_id": "sess_xyz789"
    }
    ```
</details>

<details>
<summary><b>🧠 ChromaDB Long-Term Memory</b></summary>

For every user request:
1.  The engine performs a semantic vector search on ChromaDB for memories tied to the `user_id`.
2.  Retrieved facts are injected as context in the system prompt.
3.  Following completion, a background task uses `gpt-4o-mini` to extract new core facts (e.g., "User is preparing for an interview") and commits them to the vector collection.
</details>

<details>
<summary><b>🎬 Avatar Animation Trigger Codes</b></summary>

The engine enforces structured returns mapping OpenAI outputs directly to 3D avatar animations:
*   `NOD_COMPASSION` — Empathetic listening cues.
*   `BREATHE_CALM` — Calming guidance patterns.
*   `HEAD_TILT_CURIOUS` — Thinking/analyzing states.
*   `FIST_BUMP` / `CELEBRATE` — Motivational highlights.
</details>

---

## 🚀 Quick Start

### 1. Requirements
*   Python 3.10+
*   ChromaDB (will compile locally on first startup)
*   Active OpenAI API key

### 2. Configurations Setup
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=sk-proj-your-openai-api-key
MODEL_NAME=gpt-4o
DEBUG=False
APP_TITLE="Humanic AI Companion Engine"
APP_VERSION="1.2.0"

# Optional: Set GROQ API Key to run completions on Groq instead of OpenAI
GROQ_API_KEY=gsk_your-groq-key-here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Installation & Run
Build environment and install dependencies:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Start the Uvicorn application server:
```bash
uvicorn app.main:app --reload --port 8000
```
Swagger UI will run at `http://localhost:8000/docs`.

### 4. Running Memory Verification
Execute the automated script to test ChromaDB fact extraction and context injection:
```bash
python tests/test_memory.py
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
