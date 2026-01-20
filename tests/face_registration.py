import requests
import os

# =====================================================
# CONFIG
# =====================================================
BASE_URL = "http://localhost:8000"
ENDPOINT = "/faces/register"

EMPLOYEE_ID = 36
IMAGE_PATH = "varun_test.jpg"

if not os.path.exists(IMAGE_PATH):
    raise RuntimeError("❌ Image not found")

# =====================================================
# REQUEST
# =====================================================
url = f"{BASE_URL}{ENDPOINT}"

files = {
    "file": (
        "varun_test.jpg",                 # filename
        open(IMAGE_PATH, "rb"),           # file object
        "image/jpeg",                     # ✅ IMPORTANT
    )
}

data = {
    "employee_id": EMPLOYEE_ID,
}

print("➡️  Registering face...")

resp = requests.post(
    url,
    files=files,
    data=data,
    timeout=30,
)

print("⬅️  Status:", resp.status_code)

try:
    print("📊 Response:", resp.json())
except Exception:
    print("📊 Raw:", resp.text)
