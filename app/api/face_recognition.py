from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from datetime import datetime
from typing import Optional
import os

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

# =====================================================
# 3️⃣ FACE ATTENDANCE PUNCH (🔥 MAIN API)
# =====================================================
@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    event_time = event_time or datetime.utcnow()

    # ---------- IMAGE VALIDATION ----------
    image_bytes = validate_image(file)

    # ---------- FACE IDENTIFICATION ----------
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    all_faces = get_all_faces()

    if not all_faces:
        raise HTTPException(status_code=404, detail="No employees enrolled")

    result = identify_face(all_faces, embedding)

    print(f"DEBUG punch result: {result}")  # 🐛 Debug

    if not result.get("match"):
        raise HTTPException(status_code=401, detail="Face not recognized")

    employee_id = int(result["employee_id"])
    distance = result["distance"]

    # ✅ Better confidence (threshold=1.0)
    confidence = float(np.clip(1.0 - distance, 0.0, 1.0))

    # ---------- ATTENDANCE ----------
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
                "reason": punch_result.get("reason"),
                "allowed_after": punch_result.get("allowed_after"),
            }

        return {
            "success": True,
            "employee_id": employee_id,
            "confidence": confidence,
            "distance": distance,
            "action": punch_result["action"],
        }

    except AttendanceException as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark attendance: {str(e)}",
        )

# =====================================================
# 4️⃣ FACE IDENTIFICATION ONLY (NO ATTENDANCE)
# =====================================================
@router.post("/identify")
async def identify_face_only(
    file: UploadFile = File(...),
):
    image_bytes = validate_image(file)
    embedding = extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    all_faces = get_all_faces()

    if not all_faces:
        return {
            "match": False,
            "employee_id": None,
            "message": "No employees enrolled",
        }

    result = identify_face(all_faces, embedding)

    if not result.get("match"):
        return {
            "match": False,
            "employee_id": None,
        }

    return {
        "match": True,
        "employee_id": int(result["employee_id"]),
        "distance": result["distance"],
        "confidence": float(np.clip(1.0 - result["distance"], 0.0, 1.0)),
    }
