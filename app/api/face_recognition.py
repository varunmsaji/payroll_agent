from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
import os

from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceError

router = APIRouter(prefix="/faces", tags=["Face Attendance"])

# =====================================================
# ENV CONFIG
# =====================================================
COMPRE_FACE_URL = os.getenv("COMPRE_FACE_URL", "http://localhost:8000")
API_KEY = os.getenv("FACE_API_KEY")
COLLECTION_ID = os.getenv("COLLECTION_ID", "employees")

if not API_KEY:
    raise RuntimeError("FACE_API_KEY not set")

# =====================================================
# CONSTANTS
# =====================================================
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

MIN_MATCH_CONFIDENCE = 0.85


# =====================================================
# UTILS
# =====================================================
def validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid image type")

    contents = file.file.read()

    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image too large")

    file.file.seek(0)
    return contents


def compreface_headers() -> Dict[str, str]:
    return {"x-api-key": API_KEY}


def compreface_file(file: UploadFile, image_bytes: bytes):
    return {
        "file": (
            file.filename,
            image_bytes,
            file.content_type,
        )
    }

@router.post("/register")
async def register_face(
    employee_id: int = Form(...),
    file: UploadFile = File(...),
):
    image_bytes = validate_image(file)

    url = f"{COMPRE_FACE_URL}/api/v1/recognition/faces"
    params = {
        "subject": str(employee_id),
        "collectionId": COLLECTION_ID,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers=compreface_headers(),
            params=params,
            files={
                "file": (
                    file.filename,
                    image_bytes,
                    file.content_type,
                )
            },
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(500, f"CompreFace error: {resp.text}")

    data = resp.json()

    # ✅ Handle BOTH CompreFace success formats
    if "faces" in data:
        faces_count = len(data["faces"])
    elif "image_id" in data:
        faces_count = 1
    else:
        raise HTTPException(400, "Invalid CompreFace response")

    if faces_count != 1:
        raise HTTPException(400, "Exactly one face must be present")

    return {
        "success": True,
        "employee_id": employee_id,
        "message": "Face registered successfully",
        "image_id": data.get("image_id"),
    }



# =====================================================
# 2️⃣ VERIFY FACE (RECOGNITION ONLY)
# =====================================================
@router.post("/verify")
async def verify_face(
    file: UploadFile = File(...),
):
    """
    Verify face and return matched employee_id
    """
    image_bytes = validate_image(file)

    url = f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
    params = {"collectionId": COLLECTION_ID}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers=compreface_headers(),
            params=params,
            files=compreface_file(file, image_bytes),
        )

    if resp.status_code != 200:
        raise HTTPException(500, f"CompreFace error: {resp.text}")

    data = resp.json()
    results = data.get("result", [])

    if not results or not results[0].get("subjects"):
        raise HTTPException(401, "Face not recognized")

    subject = results[0]["subjects"][0]

    return {
        "employee_id": int(subject["subject"]),
        "confidence": subject["similarity"],
    }


# =====================================================
# 3️⃣ FACE ATTENDANCE PUNCH (END-TO-END)
# =====================================================
@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
):
    """
    Full flow:
    - Verify face
    - Mark attendance
    """
    image_bytes = validate_image(file)

    # --- Face recognition ---
    url = f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
    params = {"collectionId": COLLECTION_ID}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers=compreface_headers(),
            params=params,
            files=compreface_file(file, image_bytes),
        )

    if resp.status_code != 200:
        raise HTTPException(500, f"CompreFace error: {resp.text}")

    data = resp.json()
    results = data.get("result", [])

    if not results or not results[0].get("subjects"):
        raise HTTPException(401, "Face not recognized")

    subject = results[0]["subjects"][0]
    employee_id = int(subject["subject"])
    confidence = subject["similarity"]

    if confidence < MIN_MATCH_CONFIDENCE:
        raise HTTPException(401, "Face confidence too low")

    # --- Attendance punch ---
    try:
        attendance = AttendanceService.process_punch(
            employee_id=employee_id,
            event_time=datetime.utcnow(),
            source="face",
            meta={
                "confidence": confidence,
                "device": "face_scanner",
            },
        )
    except AttendanceError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "employee_id": employee_id,
        "confidence": confidence,
        "attendance": attendance,
    }
