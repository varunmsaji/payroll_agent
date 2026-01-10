from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from datetime import datetime, date
import httpx

from app.services.attendence_services import AttendanceService
from app.database.attendence import AttendanceEventDB
from app.database.attendence import ShiftDB


router = APIRouter(prefix="/faces", tags=["Faces"])

# =============================
# COMPRE FACE CONFIG
# =============================
COMPRE_FACE_URL = "http://localhost:8001"
API_KEY = "788f96a2-f526-4ab0-83b1-2e8cecaa520b"
COLLECTION_ID = "b2f6dbb6-eca2-4472-a858-ac9cc67d4e34"

# =============================
# IMAGE VALIDATION
# =============================
ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

MAX_SIZE_MB = 5
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


async def validate_image(upload: UploadFile) -> bytes:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {upload.content_type}",
        )

    data = await upload.read()

    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max allowed {MAX_SIZE_MB} MB",
        )

    return data


# =============================
# REGISTER FACE
# =============================
@router.post("/register")
async def register_face(
    employee_id: str = Form(...),   # UUID
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    image_bytes = await validate_image(image)

    url = (
        f"{COMPRE_FACE_URL}/api/v1/recognition/faces"
        f"?collection_id={COLLECTION_ID}&subject={employee_id}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={"x-api-key": API_KEY},
            files={"file": (image.filename, image_bytes, image.content_type)},
        )

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)

    return {
        "message": "Face registered successfully",
        "employee_id": employee_id,
        "location": {"lat": latitude, "lng": longitude},
        "raw": resp.json(),
    }


    
@router.post("/attendance")
async def face_attendance(
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    # 1️⃣ Validate image
    image_bytes = await validate_image(image)

    # 2️⃣ Face recognition
    recognize_url = (
        f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
        f"?collection_id={COLLECTION_ID}&limit=1"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            recognize_url,
            headers={"x-api-key": API_KEY},
            files={"file": (image.filename, image_bytes, image.content_type)},
        )

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)

    data = resp.json()
    results = data.get("result", [])

    if not results:
        return {
            "recognized": False,
            "message": "Face not recognized",
        }

    employee_id = results[0]["subjects"][0]["subject"]

    # 3️⃣ SESSION-AWARE EVENT FETCH (FIX)
    today = date.today()

    shift = ShiftDB.get_employee_shift(employee_id, today)
    window_start, window_end, _, _, _ = AttendanceService._get_shift_window(
        shift, today
    )

    events = AttendanceEventDB.get_events_for_window(
        employee_id,
        window_start,
        datetime.now(),
    )

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "face",
    }

    # 4️⃣ Decide attendance action (NOW CORRECT)
    try:
        if not events:
            action = "check_in"
            result = AttendanceService.check_in(
                employee_id,
                source="face",
                meta=meta,
            )

        else:
            last_event = events[-1]["event_type"]

            if last_event == "check_in":
                action = "break_start"
                result = AttendanceService.break_start(
                    employee_id,
                    source="face",
                    meta=meta,
                )

            elif last_event == "break_start":
                action = "break_end"
                result = AttendanceService.break_end(
                    employee_id,
                    source="face",
                    meta=meta,
                )

            else:
                action = "check_out"
                result = AttendanceService.check_out(
                    employee_id,
                    source="face",
                    meta=meta,
                )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "recognized": True,
        "employee_id": employee_id,
        "action": action,
        "location": meta,
        "attendance_event": result,
    }
