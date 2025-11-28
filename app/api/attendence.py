# app/routers/attendance_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from app.services.attendence_services import AttendanceService
from app.database.connection import get_connection
from app.database.attendence import AttendanceDB


router = APIRouter(prefix="/hrms/attendance", tags=["Attendance"])

from typing import Optional, Dict
from pydantic import BaseModel

class AttendanceAction(BaseModel):
    employee_id: int
    source: Optional[str] = "manual"
    meta: Optional[Dict] = None


# ------------------------
# EMPLOYEE ACTIONS
# ------------------------

@router.post("/check-in")
def check_in(payload: AttendanceAction):
    try:
        return AttendanceService.check_in(
            payload.employee_id,
            payload.source or "manual",
            payload.meta
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-out")
def check_out(payload: AttendanceAction):
    try:
        return AttendanceService.check_out(
            payload.employee_id,
            payload.source or "manual",
            payload.meta
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/break/start")
def break_start(payload: AttendanceAction):
    try:
        return AttendanceService.break_start(
            payload.employee_id,
            payload.source or "manual",
            payload.meta
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/break/end")
def break_end(payload: AttendanceAction):
    try:
        return AttendanceService.break_end(
            payload.employee_id,
            payload.source or "manual",
            payload.meta
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------
# ADMIN / SYSTEM ACTIONS
# ------------------------

@router.post("/recalculate/{employee_id}")
def recalc(employee_id: int, dt: date):
    try:
        return AttendanceService.recalculate_for_date(employee_id, dt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employee/{employee_id}")
def get_attendance(employee_id: int, start_date: date, end_date: date):
    try:
        return AttendanceDB.get_attendance_range(employee_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lock/{employee_id}")
def lock_attendance(employee_id: int, dt: date):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE attendance
            SET is_payroll_locked = TRUE,
                locked_at = NOW()
            WHERE employee_id = %s AND date = %s;
        """, (employee_id, dt))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Attendance locked for payroll"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
