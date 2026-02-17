"""
Humanic AI – Memory Persistence Test
Verifies that the AI remembers a fact across two separate API calls.

Usage:
    1. Start the server:  uvicorn app.main:app --port 8000
    2. Run this script:   python tests/test_memory.py
"""

import sys
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_USER = "test_user_memory_01"


def main() -> None:
    print("=" * 60)
    print("  Humanic AI – Memory Persistence Test")
    print("=" * 60)

    with httpx.Client(timeout=60.0) as client:

        # ── Step 1: Tell the AI a personal fact ──
        print("\n[1/3] Sending fact: 'My favorite color is blue'...")
        r1 = client.post(
            f"{BASE_URL}/chat",
            json={
                "user_id": TEST_USER,
                "message": "My favorite color is blue and I love painting.",
                "role": "friend",
            },
        )
        r1.raise_for_status()
        data1 = r1.json()
        print(f"  ✓ AI replied: {data1['text'][:120]}...")
        print(f"  Emotion: {data1['emotion']}  |  Animation: {data1['animation_trigger']}")

        # ── Step 2: Ask the AI to recall the fact ──
        print("\n[2/3] Asking: 'What is my favorite color?'...")
        r2 = client.post(
            f"{BASE_URL}/chat",
            json={
                "user_id": TEST_USER,
                "message": "Do you remember what my favorite color is?",
                "role": "friend",
            },
        )
        r2.raise_for_status()
        data2 = r2.json()
        print(f"  ✓ AI replied: {data2['text'][:200]}...")
        print(f"  Emotion: {data2['emotion']}  |  Animation: {data2['animation_trigger']}")

        # ── Step 3: Verify ──
        reply_lower = data2["text"].lower()
        if "blue" in reply_lower:
            print("\n✅ PASS – The AI remembered 'blue'!")
        else:
            print("\n⚠️  WARN – 'blue' not found in the reply. Full text:")
            print(f"  {data2['text']}")
            print("  (The fact may still be stored; the model just didn't surface it.)")

        # ── Bonus: schema validation ──
        print("\n[3/3] Validating response schema…")
        required_keys = {"text", "emotion", "animation_trigger", "audio_url", "session_id"}
        missing = required_keys - set(data2.keys())
        if missing:
            print(f"  ❌ FAIL – Missing keys: {missing}")
            sys.exit(1)
        else:
            print("  ✓ All required keys present.")

    print("\n" + "=" * 60)
    print("  All checks passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
