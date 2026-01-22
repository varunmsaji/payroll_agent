from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from datetime import datetime
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

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_POSES = {"front", "left", "right"}


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
# 1️⃣ REGISTER FACE (STRICT 3-POSE ENROLLMENT)
# =====================================================
@router.post("/register")
async def register_face(
    employee_id: int = Query(...),
    photo_type: str = Query(..., regex="^(front|left|right)$"),
    file: UploadFile = File(...),
):
    """
    Register ONE face per pose: front | left | right
    Max 3 photos per employee.
    """

    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    stored = get_faces(str(employee_id))

    if len(stored) >= 3:
        raise HTTPException(
            status_code=400,
            detail="Max 3 photos allowed (front, left, right)"
        )

    save_face(str(employee_id), embedding)

    return {
        "success": True,
        "employee_id": employee_id,
        "photo_type": photo_type,
        "total_photos": len(stored) + 1,
    }


# =====================================================
# 2️⃣ IDENTIFY FACE ONLY (NO ATTENDANCE)
# =====================================================
@router.post("/identify")
async def identify_face_only(file: UploadFile = File(...)):
    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    all_faces = get_all_faces()
    if not all_faces:
        return {"match": False, "employee_id": None}

    result = identify_face(all_faces, embedding)

    if not result.get("match"):
        return {"match": False, "employee_id": None}

    return {
        "match": True,
        "employee_id": int(result["employee_id"]),
        "distance": float(result["distance"]),
    }


# =====================================================
# 3️⃣ FACE ATTENDANCE (PRODUCTION)
# =====================================================
@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    event_time = event_time or datetime.utcnow()

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
    confidence = round(max(0.0, 1.0 - result["distance"]), 4)

    try:
        punch = AttendanceService.process_punch(
            employee_id=employee_id,
            event_time=event_time,
            source="face",
            meta={"confidence": confidence, "device": "face_scanner"},
        )

        if punch.get("ignored"):
            return {"success": False, **punch}

        return {
            "success": True,
            "employee_id": employee_id,
            "confidence": confidence,
            "action": punch["action"],
        }

    except AttendanceException as e:
        raise HTTPException(status_code=400, detail=str(e))
