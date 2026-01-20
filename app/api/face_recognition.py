from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from datetime import datetime
from typing import Optional
import httpx
import os

from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceError

router = APIRouter(prefix="/faces", tags=["Face Attendance"])

COMPRE_FACE_URL = os.getenv("COMPRE_FACE_URL")
API_KEY = os.getenv("FACE_API_KEY")
COLLECTION_ID = os.getenv("COLLECTION_ID")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024


def validate_image(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid image type")

    data = file.file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image too large")

    file.file.seek(0)
    return data


def compreface_headers():
    return {"x-api-key": API_KEY}


@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    print("\n================ FACE PUNCH =================")

    event_time = event_time or datetime.utcnow()
    print("event_time:", event_time)

    image_bytes = validate_image(file)

    # -------------------------------------------------
    # ✅ CORRECT MULTIPART FORMAT (FIX)
    # -------------------------------------------------
    files = {
        "file": (
            file.filename or "face.jpg",
            image_bytes,
            file.content_type,
        )
    }

    # -------------------------------------------------
    # FACE RECOGNITION
    # -------------------------------------------------
    url = f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
    params = {"collectionId": COLLECTION_ID}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers=compreface_headers(),
            params=params,
            files=files,   # ✅ FIXED
        )

    print("CompreFace status:", resp.status_code)

    if resp.status_code != 200:
        print("CompreFace error:", resp.text)
        raise HTTPException(500, resp.text)

    data = resp.json()
    print("CompreFace response:", data)

    results = data.get("result", [])

    if not results or not results[0].get("subjects"):
        raise HTTPException(401, "Face not recognized")

    subject = results[0]["subjects"][0]
    employee_id = int(subject["subject"])
    confidence = float(subject["similarity"])

    print("Recognized employee:", employee_id, "confidence:", confidence)

    # -------------------------------------------------
    # ATTENDANCE
    # -------------------------------------------------
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

    print("Attendance action:", attendance.get("action"))
    print("================ END FACE PUNCH ================\n")

    return {
        "success": True,
        "employee_id": employee_id,
        "confidence": confidence,
        "action": attendance.get("action"),
    }
