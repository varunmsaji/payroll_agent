from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict
from psycopg2.extras import RealDictCursor

from app.services.attendence_services import AttendanceService
from app.database.connection import get_connection

router = APIRouter(prefix="/hrms/attendance", tags=["Attendance - Actions"])


class AttendanceAction(BaseModel):
    employee_id: int
    source: Optional[str] = "manual"
    meta: Optional[Dict] = None


class AttendanceOverride(BaseModel):
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    net_hours: Optional[float] = None
    status: Optional[str] = None


# -----------------------
# EMPLOYEE ACTIONS
# -----------------------

@router.post("/check-in")
def check_in(payload: AttendanceAction):
    return AttendanceService.check_in(payload.employee_id, payload.source, payload.meta)


@router.post("/check-out")
def check_out(payload: AttendanceAction):
    return AttendanceService.check_out(payload.employee_id, payload.source, payload.meta)


@router.post("/break/start")
def break_start(payload: AttendanceAction):
    return AttendanceService.break_start(payload.employee_id, payload.source, payload.meta)


@router.post("/break/end")
def break_end(payload: AttendanceAction):
    return AttendanceService.break_end(payload.employee_id, payload.source, payload.meta)


# -----------------------
# PAYROLL LOCK / UNLOCK
# -----------------------

@router.post("/lock/{employee_id}")
def lock_attendance(employee_id: int, dt: date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE attendance
        SET is_payroll_locked = TRUE, locked_at = NOW()
        WHERE employee_id = %s AND date = %s;
    """, (employee_id, dt))

    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Attendance locked"}


@router.post("/unlock/{employee_id}")
def unlock_attendance(employee_id: int, dt: date):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE attendance
        SET is_payroll_locked = FALSE, locked_at = NULL
        WHERE employee_id = %s AND date = %s;
    """, (employee_id, dt))

    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Attendance unlocked"}


# -----------------------
# HR MANUAL OVERRIDE
# -----------------------

@router.put("/override/{employee_id}")
def override_attendance(employee_id: int, dt: date, payload: AttendanceOverride):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        check_in = payload.check_in
        check_out = payload.check_out

        if check_in and len(check_in) == 5:
            check_in = f"{dt} {check_in}:00"

        if check_out and len(check_out) == 5:
            check_out = f"{dt} {check_out}:00"

        cur.execute("""
            UPDATE attendance
            SET check_in = COALESCE(%s, check_in),
                check_out = COALESCE(%s, check_out),
                net_hours = COALESCE(%s, net_hours),
                status = COALESCE(%s, status)
            WHERE employee_id = %s
              AND date = %s
              AND is_payroll_locked = FALSE
            RETURNING *;
        """, (
            check_in,
            check_out,
            payload.net_hours,
            payload.status,
            employee_id,
            dt
        ))

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=400,
                detail="Attendance is locked or record not found"
            )

        conn.commit()
        return {"message": "Attendance overridden successfully", "updated": row}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()


# -----------------------
# RECALCULATE
# -----------------------

@router.post("/recalculate/{employee_id}")
def recalc_attendance(employee_id: int, dt: date):
    AttendanceService.recalculate_for_date(employee_id, dt)
    return {"message": "Attendance recalculated"}
