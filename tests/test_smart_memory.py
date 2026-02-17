"""
Humanic AI – Smart Memory Test
Verifies that the intelligent extraction catches nuanced facts that
old regex patterns would have missed entirely.

Usage:
    1. Start the server:  uvicorn app.main:app --port 8000
    2. Run this script:   python tests/test_smart_memory.py
"""

import json
import sys
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_USER = "test_smart_memory_user"

# ── Visual helpers ──

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CHECK = "✅"
CROSS = "❌"
ARROW = "→"
BRAIN = "🧠"
DOG = "🐕"
MAG = "🔍"


def header(title: str) -> None:
    width = 64
    print(f"\n{CYAN}{'━' * width}")
    print(f"  {BOLD}{title}{RESET}{CYAN}")
    print(f"{'━' * width}{RESET}\n")


def step(num: int, total: int, msg: str) -> None:
    bar = f"[{'█' * num}{'░' * (total - num)}]"
    print(f"  {YELLOW}{bar}{RESET}  {BOLD}Step {num}/{total}{RESET} {DIM}│{RESET} {msg}")


def show_response(data: dict) -> None:
    print(f"\n  {CYAN}┌─────────────────────────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}  {BOLD}AI Response{RESET}")
    print(f"  {CYAN}├─────────────────────────────────────────────────────────┤{RESET}")

    # Text (word-wrapped)
    text = data["text"]
    max_w = 53
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    for line in lines:
        print(f"  {CYAN}│{RESET}  {line}")

    print(f"  {CYAN}├─────────────────────────────────────────────────────────┤{RESET}")
    print(f"  {CYAN}│{RESET}  Emotion:   {GREEN}{data['emotion']}{RESET}")
    print(f"  {CYAN}│{RESET}  Animation: {GREEN}{data['animation_trigger']}{RESET}")
    print(f"  {CYAN}│{RESET}  Session:   {DIM}{data['session_id']}{RESET}")
    print(f"  {CYAN}└─────────────────────────────────────────────────────────┘{RESET}\n")


def main() -> None:
    header(f"{BRAIN}  Humanic AI – Smart Memory Test")

    with httpx.Client(timeout=60.0) as client:

        # ── Step 1: Send a nuanced message (regex would miss this) ──
        step(1, 3, f"{DOG} Sending nuanced message about Rex...")
        message = "I'm really worried about my dog, Rex, he's been sick all week."
        print(f"\n  {ARROW} Message: {DIM}\"{message}\"{RESET}\n")

        r1 = client.post(
            f"{BASE_URL}/chat",
            json={"user_id": TEST_USER, "message": message, "role": "therapist"},
        )
        r1.raise_for_status()
        data1 = r1.json()
        show_response(data1)

        # ── Step 2: Ask the AI to recall Rex ──
        step(2, 3, f"{MAG} Asking AI to recall what it knows...")
        recall_msg = "Do you remember anything about my pet?"
        print(f"\n  {ARROW} Message: {DIM}\"{recall_msg}\"{RESET}\n")

        r2 = client.post(
            f"{BASE_URL}/chat",
            json={"user_id": TEST_USER, "message": recall_msg, "role": "therapist"},
        )
        r2.raise_for_status()
        data2 = r2.json()
        show_response(data2)

        # ── Step 3: Verify ──
        step(3, 3, "Checking if AI remembered Rex...")

        reply = data2["text"].lower()
        found_rex = "rex" in reply
        found_sick = any(w in reply for w in ["sick", "ill", "unwell", "worried", "health"])

        print()
        if found_rex:
            print(f"  {CHECK}  {GREEN}PASS{RESET} – AI remembered the dog's name  {BOLD}\"Rex\"{RESET}")
        else:
            print(f"  {CROSS}  {RED}MISS{RESET} – \"Rex\" not found in reply")

        if found_sick:
            print(f"  {CHECK}  {GREEN}PASS{RESET} – AI recalled Rex being sick/worried")
        else:
            print(f"  {CROSS}  {YELLOW}MISS{RESET} – Sickness context not surfaced")

        # ── Final verdict ──
        print()
        if found_rex:
            print(f"  {CYAN}{'━' * 50}{RESET}")
            print(f"  {CHECK}  {GREEN}{BOLD}SMART MEMORY WORKS!{RESET}")
            print(f"  {DIM}     Old regex would have missed \"worried about")
            print(f"       my dog Rex\" — no pattern matched it.{RESET}")
            print(f"  {CYAN}{'━' * 50}{RESET}")
        else:
            print(f"  {CYAN}{'━' * 50}{RESET}")
            print(f"  {YELLOW}{BOLD}⚠  PARTIAL{RESET} – Facts may be stored but AI")
            print(f"     didn't surface them in this response.")
            print(f"  {CYAN}{'━' * 50}{RESET}")
            sys.exit(1)

    print()


if __name__ == "__main__":
    main()
