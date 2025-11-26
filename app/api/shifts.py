from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.database.shifts_db import ShiftDB
from app.database.employee_shift_db import EmployeeShiftDB

router = APIRouter(prefix="/hrms/shifts", tags=["Shifts"])


# ============================================================
# 1️⃣ GET ALL SHIFTS
# ============================================================
@router.get("/")
def list_shifts():
    return ShiftDB.get_all()


# ============================================================
# 2️⃣ GET ONE SHIFT
# ============================================================
@router.get("/{shift_id}")
def get_shift(shift_id: int):
    shift = ShiftDB.get_one(shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


# ============================================================
# 3️⃣ CREATE NEW SHIFT (NOW SUPPORTS BREAKS)
# ============================================================
@router.post("/")
def create_shift(payload: Dict[str, Any]):
    """
    Example:
    {
        "shift_name": "Morning Shift",
        "start_time": "07:00:00",
        "end_time": "15:00:00",
        "is_night_shift": false,
        "break_start": "13:00:00",
        "break_end": "13:30:00",
        "break_minutes": 30
    }
    """
    return ShiftDB.add_shift(payload)


# ============================================================
# 4️⃣ UPDATE SHIFT (NOW SUPPORTS BREAKS)
# ============================================================
@router.put("/{shift_id}")
def update_shift(shift_id: int, payload: Dict[str, Any]):
    updated = ShiftDB.update_shift(shift_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Shift not found")
    return updated


# ============================================================
# 5️⃣ DELETE SHIFT
# ============================================================
@router.delete("/{shift_id}")
def delete_shift(shift_id: int):
    deleted = ShiftDB.delete_shift(shift_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Shift not found")
    return {"deleted": True}


# ============================================================
# 6️⃣ ASSIGN SHIFT TO EMPLOYEE
# ============================================================
@router.post("/assign")
def assign_shift(payload: Dict[str, Any]):
    """
    payload = {
        "employee_id": 1,
        "shift_id": 2,
        "effective_from": "2025-01-15"
    }
    """
    return EmployeeShiftDB.assign_shift(
        payload["employee_id"],
        payload["shift_id"],
        payload["effective_from"]
    )


# ============================================================
# 7️⃣ EMPLOYEE SHIFT HISTORY
# ============================================================
@router.get("/employee/{employee_id}/history")
def employee_shift_history(employee_id: int):
    return EmployeeShiftDB.get_shift_history(employee_id)
