# app/api/shifts_router.py

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from datetime import time, date

from app.database.shifts_db import ShiftDB
from app.database.employee_shift_db import EmployeeShiftDB

router = APIRouter(prefix="/hrms/shifts", tags=["Shifts"])


# ============================================================
# ✅ SCHEMAS
# ============================================================

class ShiftCreate(BaseModel):
    shift_name: str
    start_time: time
    end_time: time
    is_night_shift: Optional[bool] = False
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    break_minutes: Optional[int] = 0


class ShiftAssign(BaseModel):
    employee_id: int
    shift_id: int
    effective_from: date


# ============================================================
# ✅ 1️⃣ LIST SHIFTS (PAGINATED)
# ============================================================
@router.get("/")
def list_shifts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    return ShiftDB.get_all(page, limit)


# ============================================================
# ✅ 2️⃣ GET ONE
# ============================================================
@router.get("/{shift_id}")
def get_shift(shift_id: int):
    shift = ShiftDB.get_one(shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


# ============================================================
# ✅ 3️⃣ CREATE SHIFT (VALIDATED)
# ============================================================
@router.post("/")
def create_shift(payload: ShiftCreate):

    # ✅ Time validation
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "End time must be after start time")

    if payload.break_start and payload.break_end:
        if payload.break_end <= payload.break_start:
            raise HTTPException(400, "Invalid break time range")

    try:
        return ShiftDB.add_shift(payload.dict())
    except Exception as e:
        raise HTTPException(400, str(e))


# ============================================================
# ✅ 4️⃣ UPDATE SHIFT
# ============================================================
@router.put("/{shift_id}")
def update_shift(shift_id: int, payload: ShiftCreate):

    updated = ShiftDB.update_shift(shift_id, payload.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="Shift not found")

    return updated


# ============================================================
# ✅ 5️⃣ DELETE SHIFT (SOFT DELETE)
# ============================================================
@router.delete("/{shift_id}")
def delete_shift(shift_id: int):
    deleted = ShiftDB.delete_shift(shift_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Shift not found")
    return {"deleted": True}


# ============================================================
# ✅ 6️⃣ ASSIGN SHIFT TO EMPLOYEE (SAFE)
# ============================================================
@router.post("/assign")
def assign_shift(payload: ShiftAssign):
    return EmployeeShiftDB.assign_shift(
        payload.employee_id,
        payload.shift_id,
        payload.effective_from
    )


# ============================================================
# ✅ 7️⃣ SHIFT HISTORY
# ============================================================
@router.get("/employee/{employee_id}/history")
def employee_shift_history(employee_id: int):
    return EmployeeShiftDB.get_shift_history(employee_id)
