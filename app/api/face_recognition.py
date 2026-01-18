from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from datetime import datetime
import httpx

from app.services.attendence import AttendanceService
from app.services.attendence.exceptions import AttendanceError
from app.database.attendence import AttendanceEventDB, ShiftDB

router = APIRouter(prefix="/faces", tags=["Face Attendance"])

COMPRE_FACE_URL = os.getenv("COMPRE_FACE_URL")  
API_KEY = os.getenv("FACE_API_KEY")
COLLECTION_ID = os.getenv("COLLECTION_ID")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024


async def validate_image(upload: UploadFile) -> bytes:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Unsupported image type")

    data = await upload.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image too large")

    return data


@router.post("/attendance")
async def face_attendance(
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    image_bytes = await validate_image(image)

    recognize_url = (
        f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
        f"?collection_id={COLLECTION_ID}&limit=1"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            recognize_url,
            headers={"x-api-key": API_KEY},
            files={"file": (image.filename, image_bytes, image.content_type)},
        )

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)

    results = resp.json().get("result", [])
    if not results:
        return {"recognized": False, "message": "Face not recognized"}

    employee_id = int(results[0]["subjects"][0]["subject"])

    now = datetime.utcnow()
    today = now.date()

    shift = ShiftDB.get_employee_shift(employee_id, today)
    window_start, _, _, _, _ = AttendanceService._get_shift_window(shift, today)

    events = AttendanceEventDB.get_events_for_window(
        employee_id, window_start, now
    )

    meta = {
        "latitude": latitude,
        "longitude": longitude,
        "method": "face",
    }

    try:
        if not events:
            action = "check_in"
            event = AttendanceService.check_in(
                employee_id, source="face", meta=meta, now=now
            )

        else:
            last = events[-1]["event_type"]

            if last == "check_in":
                action = "break_start"
                event = AttendanceService.break_start(
                    employee_id, source="face", meta=meta, now=now
                )

            elif last == "break_start":
                action = "break_end"
                event = AttendanceService.break_end(
                    employee_id, source="face", meta=meta, now=now
                )

            else:
                action = "check_out"
                event = AttendanceService.check_out(
                    employee_id, source="face", meta=meta, now=now
                )

    except AttendanceError as e:
        raise HTTPException(400, str(e))

    return {
        "recognized": True,
        "employee_id": employee_id,
        "action": action,
        "attendance_event": event,
        "timestamp": now.isoformat(),
        "location": meta,
    }
