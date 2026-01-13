from fastapi import APIRouter, HTTPException
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection

router = APIRouter(
    prefix="/attendance/debug",
    tags=["Attendance Debug"],
)


# =========================================================
# 1️⃣ CLEANUP ENDPOINT (TEST ONLY)
# =========================================================
@router.post("/cleanup")
def cleanup_employee_attendance(payload: dict):
    employee_id = payload.get("employee_id")

    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM attendance_events WHERE employee_id = %s;", (employee_id,))
    cur.execute("DELETE FROM attendance WHERE employee_id = %s;", (employee_id,))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "success": True,
        "message": f"Attendance data cleared for employee {employee_id}"
    }


# =========================================================
# 2️⃣ FETCH FINAL ATTENDANCE FOR DATE
# =========================================================
@router.get("/{employee_id}/{attendance_date}")
def get_attendance(employee_id: int, attendance_date: date):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            employee_id,
            date,
            check_in,
            check_out,
            net_hours,
            break_minutes,
            late_minutes,
            early_exit_minutes,
            overtime_minutes,
            status
        FROM attendance
        WHERE employee_id = %s AND date = %s;
        """,
        (employee_id, attendance_date),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Attendance not found")

    return row
