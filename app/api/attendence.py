# app/routers/attendance_router.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict, List
from psycopg2.extras import RealDictCursor

from app.services.attendence_services import AttendanceService
from app.database.connection import get_connection
from app.database.attendence import AttendanceDB, AttendanceEventDB

router = APIRouter(prefix="/hrms/attendance", tags=["Attendance"])


# ============================
# SCHEMAS
# ============================

class AttendanceAction(BaseModel):
    employee_id: int
    source: Optional[str] = "manual"
    meta: Optional[Dict] = None


class AttendanceOverride(BaseModel):
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    net_hours: Optional[float] = None
    status: Optional[str] = None


# ============================
# EMPLOYEE ACTIONS
# ============================

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


# ✅ Employee Today's Attendance Status (For Dashboard)
@router.get("/today/{employee_id}")
def today_status(employee_id: int):
    today = date.today()
    data = AttendanceDB.get_by_employee_and_date(employee_id, today)
    if not data:
        AttendanceService.recalculate_for_date(employee_id, today)
        data = AttendanceDB.get_by_employee_and_date(employee_id, today)
    return data


# ============================
# EMPLOYEE HISTORY
# ============================

@router.get("/employee/{employee_id}")
def get_attendance(employee_id: int, start_date: date, end_date: date):
    return AttendanceDB.get_attendance_range(employee_id, start_date, end_date)


# ============================
# HR / ADMIN DASHBOARD
# ============================

# ✅ Company Daily Attendance Table
@router.get("/company")
def company_attendance(date_: date = Query(default=date.today())):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT a.*, e.first_name, e.last_name, e.department
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.date = %s
        ORDER BY e.first_name;
    """, (date_,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ✅ Team Attendance (Manager View)
@router.get("/team/{manager_id}")
def team_attendance(manager_id: int, date_: date = Query(default=date.today())):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT a.*, e.first_name, e.last_name
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE e.manager_id = %s AND a.date = %s;
    """, (manager_id, date_))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ✅ Late Report
@router.get("/reports/late")
def late_report(start_date: date, end_date: date):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT a.*, e.first_name, e.department
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.is_late = TRUE
          AND a.date BETWEEN %s AND %s;
    """, (start_date, end_date))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ✅ Overtime Report
@router.get("/reports/overtime")
def overtime_report(start_date: date, end_date: date):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT a.*, e.first_name
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.is_overtime = TRUE
          AND a.date BETWEEN %s AND %s;
    """, (start_date, end_date))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ============================
# RAW LOGS (AUDIT)
# ============================

@router.get("/logs/{employee_id}")
def attendance_logs(employee_id: int):
    return AttendanceEventDB.get_all_events_for_employee(employee_id)


# ============================
# PAYROLL LOCK CONTROL
# ============================

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


# ✅ UNLOCK (ADMIN ONLY)
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


# ============================
# HR MANUAL OVERRIDE
# ============================
@router.put("/override/{employee_id}")
def override_attendance(employee_id: int, dt: date, payload: AttendanceOverride):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ✅ AUTO-CONVERT TIME-ONLY INPUTS TO FULL TIMESTAMP
        check_in = payload.check_in
        check_out = payload.check_out

        if check_in and len(check_in) == 5:  # "09:00"
            check_in = f"{dt} {check_in}:00"

        if check_out and len(check_out) == 5:  # "18:00"
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
        return {
            "message": "Attendance overridden successfully",
            "updated": row
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()


@router.get("/employees")
def attendance_employee_list():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            e.employee_id,
            e.first_name,
            e.last_name,
            e.department,
            s.shift_name
        FROM employees e
        LEFT JOIN employee_shifts es ON es.employee_id = e.employee_id
        LEFT JOIN shifts s ON s.shift_id = es.shift_id
        ORDER BY e.first_name;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@router.get("/calendar/{employee_id}")
def calendar_attendance(
    employee_id: int,
    start_date: date,
    end_date: date
):
    return AttendanceDB.get_attendance_range(
        employee_id, start_date, end_date
    )



@router.get("/locked/{employee_id}")
def locked_attendance(employee_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM attendance
        WHERE employee_id = %s
          AND is_payroll_locked = TRUE
        ORDER BY date DESC;
    """, (employee_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@router.post("/recalculate/{employee_id}")
def recalc_attendance(employee_id: int, dt: date):
    AttendanceService.recalculate_for_date(employee_id, dt)
    return {"message": "Attendance recalculated"}


@router.get("/is-locked/{employee_id}")
def is_locked(employee_id: int, dt: date):
    data = AttendanceDB.get_by_employee_and_date(employee_id, dt)
    return {
        "is_locked": bool(data and data.get("is_payroll_locked", False))
    }
