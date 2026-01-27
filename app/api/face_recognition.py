# app/api/faces.py

from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.utils.logging_config import get_logger, log_exception
from datetime import datetime, timezone
from typing import Optional
import time   # ✅ ADD THIS

import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

logger = get_logger(__name__)

from app.database.face_recognition_insight import (
    get_all_faces,
    get_faces,
    save_face,
)
from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceException
from app.services.face_engine import (
    compare_embeddings,
    extract_embedding,
    identify_face,
)

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
    logger.debug(f"Validating image: {file.filename}, type: {file.content_type}")

    if file.content_type not in ALLOWED_TYPES:
        logger.warning(f"Invalid image type rejected: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid image type")

    data = file.file.read()
    logger.debug(f"Image size: {len(data)} bytes")

    if len(data) > MAX_SIZE_BYTES:
        logger.warning(f"Image too large: {len(data)} bytes (max: {MAX_SIZE_BYTES})")
        raise HTTPException(status_code=400, detail="Image too large")

    file.file.seek(0)
    logger.debug("Image validation successful")
    return data


# =====================================================
# 1️⃣ REGISTER FACE (ADMIN / ONBOARDING)
# =====================================================
@router.post("/register")
async def register_face(
    employee_id: int = Query(...),
    file: UploadFile = File(...),
):
    logger.info(f"Face registration request for employee_id: {employee_id}")

    try:
        image_bytes = validate_image(file)
        embedding = extract_embedding(image_bytes)

        if embedding is None:
            logger.warning(f"No face detected in image for employee_id: {employee_id}")
            raise HTTPException(status_code=400, detail="No face detected")

        save_face(str(employee_id), embedding)
        logger.info(f"Face registered successfully for employee_id: {employee_id}")

        return {
            "success": True,
            "employee_id": employee_id,
            "message": "Face registered successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, f"Face registration failed for employee_id: {employee_id}", e)
        raise HTTPException(status_code=500, detail="Face registration failed")


# =====================================================
# 2️⃣ VERIFY FACE FOR EMPLOYEE (OPTIONAL)
# =====================================================
@router.post("/verify")
async def verify_face(
    employee_id: int = Query(...),
    file: UploadFile = File(...),
):
    logger.info(f"Face verification request for employee_id: {employee_id}")

    try:
        image_bytes = validate_image(file)
        embedding = extract_embedding(image_bytes)

        if embedding is None:
            logger.warning(f"No face detected in verification image for employee_id: {employee_id}")
            raise HTTPException(status_code=400, detail="No face detected")

        stored_embeddings = get_faces(str(employee_id))

        if not stored_embeddings:
            logger.warning(f"No registered faces found for employee_id: {employee_id}")
            raise HTTPException(status_code=404, detail="Employee not found")

        match, distance = compare_embeddings(stored_embeddings, embedding)
        confidence = float(np.clip(1.0 - distance, 0.0, 1.0))

        logger.info(
            f"Face verification for employee_id {employee_id}: match={match}, confidence={confidence:.2f}, distance={distance:.4f}"
        )

        return {
            "success": True,
            "employee_id": employee_id,
            "match": match,
            "distance": distance,
            "confidence": confidence,
            "registered_faces": len(stored_embeddings),
        }
    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, f"Face verification failed for employee_id: {employee_id}", e)
        raise HTTPException(status_code=500, detail="Face verification failed")


@router.post("/punch")
async def face_punch(
    file: UploadFile = File(...),
    event_time: Optional[datetime] = Query(None),
):
    logger.info(f"Face punch request received at {datetime.now(timezone.utc).isoformat()}")

    # ✅ ALWAYS timezone-aware
    if event_time is None:
        event_time = datetime.now(timezone.utc)
        logger.debug(f"Using current time for event: {event_time.isoformat()}")

    if event_time.tzinfo is None:
        logger.error("Received event_time without timezone information")
        raise HTTPException(
            status_code=400,
            detail="event_time must include timezone (ISO 8601)",
        )

    try:
        image_bytes = validate_image(file)
        embedding = extract_embedding(image_bytes)

        if embedding is None:
            logger.warning("No face detected in punch image")
            raise HTTPException(status_code=400, detail="No face detected")

        all_faces = get_all_faces()
        if not all_faces:
            logger.error("No employees enrolled in the system")
            raise HTTPException(status_code=404, detail="No employees enrolled")

        logger.debug(f"Identifying face among {len(all_faces)} enrolled employees")
        result = identify_face(all_faces, embedding)

        if not result.get("match"):
            logger.warning("Face not recognized - no match found")
            raise HTTPException(status_code=401, detail="Face not recognized")

        employee_id = int(result["employee_id"])
        distance = float(result["distance"])
        confidence = float(np.clip(1.0 - distance, 0.0, 1.0))

        logger.info(
            f"Face recognized: employee_id={employee_id}, confidence={confidence:.2f}, distance={distance:.4f}"
        )

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
                logger.warning(
                    f"Punch ignored for employee_id {employee_id}: {punch_result['reason']}"
                )
                return {
                    "success": False,
                    "ignored": True,
                    "employee_id": employee_id,
                    "reason": punch_result["reason"],
                }

            logger.info(
                f"Punch successful for employee_id {employee_id}: action={punch_result['action']}"
            )
            return {
                "success": True,
                "employee_id": employee_id,
                "action": punch_result["action"],
                "event_time": event_time.isoformat(),
            }

        except AttendanceException as e:
            logger.error(f"Attendance exception for employee_id {employee_id}: {str(e)}")
            raise HTTPException(
                status_code=403,
                detail={"employee_id": employee_id, "message": str(e)},
            )

        except Exception as e:
            log_exception(
                logger, f"Unexpected error processing punch for employee_id {employee_id}", e
            )
            raise HTTPException(
                status_code=500,
                detail={"employee_id": employee_id, "message": str(e)},
            )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(logger, "Unexpected error in face_punch endpoint", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/punch/test")
def test_punch(
    employee_id: int = Query(..., description="Employee ID (test mode)"),
    event_time: Optional[datetime] = Query(
        None, description="ISO 8601 datetime with timezone"
    ),
):
    request_received_at = datetime.now(timezone.utc)

    logger.warning(
        f"[TEST_PUNCH] Request received | "
        f"employee_id={employee_id} | "
        f"raw_event_time={event_time} | "
        f"server_received_at={request_received_at.isoformat()}"
    )

    # ✅ Always timezone-aware
    if event_time is None:
        event_time = datetime.now(timezone.utc)
        logger.debug(
            f"[TEST_PUNCH] No event_time provided, using server time | "
            f"event_time={event_time.isoformat()}"
        )

    # 🚨 Hard validation
    if event_time.tzinfo is None:
        logger.error(
            f"[TEST_PUNCH] event_time WITHOUT timezone | "
            f"value={event_time}"
        )
        raise HTTPException(
            status_code=400,
            detail="event_time must include timezone (ISO 8601)",
        )

    # 🔍 Log parsed & trusted time
    logger.info(
        f"[TEST_PUNCH] Parsed event_time accepted | "
        f"event_time={event_time.isoformat()} | "
        f"tzinfo={event_time.tzinfo}"
    )

    try:
        start = time.time()

        logger.info(
            f"[TEST_PUNCH] Calling AttendanceService.process_punch | "
            f"employee_id={employee_id} | "
            f"event_time={event_time.isoformat()}"
        )

        punch_result = AttendanceService.process_punch(
            employee_id=employee_id,
            event_time=event_time,
            source="test",
            meta={
                "mode": "manual_test",
                "device": "test_endpoint",
                "server_received_at": request_received_at.isoformat(),
            },
        )

        duration = time.time() - start

        logger.info(
            f"[TEST_PUNCH] process_punch completed | "
            f"duration={duration:.2f}s | "
            f"result={punch_result}"
        )

        if punch_result.get("ignored"):
            logger.warning(
                f"[TEST_PUNCH] Punch ignored | "
                f"employee_id={employee_id} | "
                f"reason={punch_result['reason']}"
            )
            return {
                "success": False,
                "ignored": True,
                "employee_id": employee_id,
                "reason": punch_result["reason"],
                "event_time": event_time.isoformat(),
            }

        logger.info(
            f"[TEST_PUNCH] Punch successful | "
            f"employee_id={employee_id} | "
            f"action={punch_result['action']}"
        )

        return {
            "success": True,
            "employee_id": employee_id,
            "action": punch_result["action"],
            "event_time": event_time.isoformat(),
            "mode": "test",
        }

    except AttendanceException as e:
        logger.error(
            f"[TEST_PUNCH] AttendanceException | "
            f"employee_id={employee_id} | "
            f"error={str(e)}"
        )
        raise HTTPException(
            status_code=403,
            detail={"employee_id": employee_id, "message": str(e)},
        )

    except Exception as e:
        log_exception(
            logger,
            f"[TEST_PUNCH] Unexpected error | employee_id={employee_id}",
            e,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
