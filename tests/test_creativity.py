"""
Humanic AI – Creativity Test
Verifies real AI connection by asking the model to invent a new color.
"""

import json
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

payload = {
    "user_id": "test_admin",
    "message": "Invent a brand new color that doesn't exist yet. Give it a name and describe what it looks like.",
    "role": "friend",
}

print("Sending request to Humanic AI...\n")

with httpx.Client(timeout=60.0) as client:
    r = client.post(f"{BASE_URL}/chat", json=payload)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, indent=2))
