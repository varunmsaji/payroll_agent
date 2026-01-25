# app/api/faces.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional
import numpy as np

from app.database.face_recognition_insight import (
    save_face,
    get_faces,
    get_all_faces,
)
from app.services.face_engine import (
    extract_embedding,
    compare_embeddings,
    identify_face,
)
from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceException

router = APIRouter(prefix="/faces", tags=["Face Attendance"])


# =====================================================
# CONFIG
# =====================================================
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024

# =====================================================
# UTILS
# =====================================================
def validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    data = file.file.read()

    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image too large")

    file.file.seek(0)
    return data

# =====================================================
# 1️⃣ REGISTER FACE (ADMIN / ONBOARDING)
# =====================================================
@router.post("/register")
async def register_face(
    employee_id: int = Query(...),
    file: UploadFile = File(...),
):
    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    save_face(str(employee_id), embedding)

    return {
        "success": True,
        "employee_id": employee_id,
        "message": "Face registered successfully",
    }

# =====================================================
# 2️⃣ VERIFY FACE FOR EMPLOYEE (OPTIONAL)
# =====================================================
@router.post("/verify")
async def verify_face(
    employee_id: int = Query(...),
    file: UploadFile = File(...),
):
    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    stored_embeddings = get_faces(str(employee_id))

    if not stored_embeddings:
        raise HTTPException(status_code=404, detail="Employee not found")

    match, distance = compare_embeddings(stored_embeddings, embedding)

    return {
        "success": True,
        "employee_id": employee_id,
        "match": match,
        "distance": distance,
        "confidence": float(np.clip(1.0 - distance, 0.0, 1.0)),  # ✅ Fixed
        "registered_faces": len(stored_embeddings),
    }

@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    # ✅ ALWAYS timezone-aware
    if event_time is None:
        event_time = datetime.now(timezone.utc)

    if event_time.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail="event_time must include timezone (ISO 8601)",
        )

    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    all_faces = get_all_faces()
    if not all_faces:
        raise HTTPException(status_code=404, detail="No employees enrolled")

    result = identify_face(all_faces, embedding)
    if not result.get("match"):
        raise HTTPException(status_code=401, detail="Face not recognized")

    employee_id = int(result["employee_id"])
    distance = float(result["distance"])
    confidence = float(np.clip(1.0 - distance, 0.0, 1.0))

    try:
        punch_result = AttendanceService.process_punch(
            employee_id=employee_id,
            event_time=event_time,
            source="face",
            meta={
                "confidence": confidence,
                "distance": distance,
                "device": "face_scanner",
            },
        )

        if punch_result.get("ignored"):
            return {
                "success": False,
                "ignored": True,
                "employee_id": employee_id,
                "reason": punch_result["reason"],
            }

        return {
            "success": True,
            "employee_id": employee_id,
            "action": punch_result["action"],
            "event_time": event_time.isoformat(),
        }

    except AttendanceException as e:
        raise HTTPException(
            status_code=403,
            detail={"employee_id": employee_id, "message": str(e)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"employee_id": employee_id, "message": str(e)},
        )
