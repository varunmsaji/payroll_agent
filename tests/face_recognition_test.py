import requests
import os
import json

# =====================================================
# CONFIG
# =====================================================
BASE_URL = "http://localhost:8000"
ENDPOINT = "/faces/verify"

IMAGE_PATH = "shah_rukh.jpg"   # image of the registered face

if not os.path.exists(IMAGE_PATH):
    raise RuntimeError("❌ test.jpeg not found")

# =====================================================
# REQUEST
# =====================================================
url = f"{BASE_URL}{ENDPOINT}"

files = {
    "file": (
        "test.jpeg",
        open(IMAGE_PATH, "rb"),
        "image/jpeg",   # 👈 IMPORTANT
    )
}

print("➡️  Verifying face...")

resp = requests.post(
    url,
    files=files,
    timeout=30,
)

print("⬅️  Status:", resp.status_code)

try:
    data = resp.json()
    print("\n📊 RESPONSE")
    print(json.dumps(data, indent=2))
except Exception:
    print("\n📊 RAW RESPONSE")
    print(resp.text)
    raise
