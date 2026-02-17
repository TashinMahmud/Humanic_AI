import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load env variables
load_dotenv()

key = os.getenv("ELEVENLABS_API_KEY")
print(f"DEBUG: Key found? {'Yes' if key else 'No'}")
if key:
    print(f"DEBUG: Key starts with: {key[:4]}...")

try:
    client = ElevenLabs(api_key=key)
    # Try to fetch voices (simplest request)
    voices = client.voices.get_all()
    print("✅ SUCCESS! API Key is working.")
    print(f"Found {len(voices.voices)} voices.")
    print(f"First voice: {voices.voices[0].name}")
except Exception as e:
    print("\n❌ ERROR: ElevenLabs rejected the key.")
    print(f"Reason: {e}")
