from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from datetime import datetime
from typing import Optional
import httpx
import os

from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceError

router = APIRouter(prefix="/faces", tags=["Face Attendance"])

# =====================================================
# CONFIG
# =====================================================
COMPRE_FACE_URL = os.getenv("COMPRE_FACE_URL")  # e.g. http://localhost:8001
API_KEY = os.getenv("FACE_API_KEY")
COLLECTION_ID = os.getenv("COLLECTION_ID")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024


# =====================================================
# UTILS
# =====================================================
def validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid image type")

    data = file.file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image too large")

    file.file.seek(0)
    return data


def compreface_headers():
    return {"x-api-key": API_KEY}


def compreface_file(file: UploadFile, data: bytes):
    """
    ✅ REQUIRED format for CompreFace
    """
    return {
        "file": (
            file.filename or "face.jpg",
            data,
            file.content_type,
        )
    }


# =====================================================
# 1️⃣ REGISTER FACE
# =====================================================
@router.post("/register")
async def register_face(
    employee_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Register a face for an employee
    """

    image_bytes = validate_image(file)

    url = f"{COMPRE_FACE_URL}/api/v1/recognition/faces"
    params = {
        "collectionId": COLLECTION_ID,
        "subject": str(employee_id),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers=compreface_headers(),
            params=params,
            files=compreface_file(file, image_bytes),
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(500, f"CompreFace error: {resp.text}")

    return {
        "success": True,
        "employee_id": employee_id,
        "message": "Face registered successfully",
        "result": resp.json(),
    }


# =====================================================
# 2️⃣ VERIFY / RECOGNIZE FACE
# =====================================================
@router.post("/verify")
async def verify_face(
    file: UploadFile = File(...),
):
    """
    Only recognize face (NO attendance)
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
        raise HTTPException(500, resp.text)

    data = resp.json()
    results = data.get("result", [])

    if not results or not results[0].get("subjects"):
        raise HTTPException(401, "Face not recognized")

    subject = results[0]["subjects"][0]

    return {
        "success": True,
        "employee_id": int(subject["subject"]),
        "confidence": float(subject["similarity"]),
    }


# =====================================================
# 3️⃣ FACE ATTENDANCE PUNCH
# =====================================================
@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    """
    Full flow:
    - Recognize face
    - Mark attendance
    """

    event_time = event_time or datetime.utcnow()
    image_bytes = validate_image(file)

    # ---------- FACE RECOGNITION ----------
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
        raise HTTPException(500, resp.text)

    data = resp.json()
    results = data.get("result", [])

    if not results or not results[0].get("subjects"):
        raise HTTPException(401, "Face not recognized")

    subject = results[0]["subjects"][0]
    employee_id = int(subject["subject"])
    confidence = float(subject["similarity"])

    # ---------- ATTENDANCE ----------
    try:
        attendance = AttendanceService.process_punch(
            employee_id=employee_id,
            event_time=event_time,
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
        "action": attendance.get("action"),
    }
