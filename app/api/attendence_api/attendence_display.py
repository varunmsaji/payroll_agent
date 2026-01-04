from fastapi import APIRouter, Query
from datetime import date
from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection
from app.database.attendence import AttendanceDB, AttendanceEventDB

router = APIRouter(prefix="/hrms/attendance", tags=["Attendance - Display"])


# -----------------------
# EMPLOYEE VIEW
# -----------------------

@router.get("/today/{employee_id}")
def today_status(employee_id: int):
    today = date.today()
    data = AttendanceDB.get_by_employee_and_date(employee_id, today)
    if not data:
        from app.services.attendence_services import AttendanceService
        AttendanceService.recalculate_for_date(employee_id, today)
        data = AttendanceDB.get_by_employee_and_date(employee_id, today)
    return data


@router.get("/employee/{employee_id}")
def get_attendance(employee_id: int, start_date: date, end_date: date):
    return AttendanceDB.get_attendance_range(employee_id, start_date, end_date)


# -----------------------
# DASHBOARDS
# -----------------------

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


# -----------------------
# REPORTS
# -----------------------

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


# -----------------------
# LOGS & CALENDAR
# -----------------------

@router.get("/logs/{employee_id}")
def attendance_logs(employee_id: int):
    return AttendanceEventDB.get_all_events_for_employee(employee_id)


@router.get("/calendar/{employee_id}")
def calendar_attendance(employee_id: int, start_date: date, end_date: date):
    return AttendanceDB.get_attendance_range(employee_id, start_date, end_date)


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


@router.get("/is-locked/{employee_id}")
def is_locked(employee_id: int, dt: date):
    data = AttendanceDB.get_by_employee_and_date(employee_id, dt)
    return {"is_locked": bool(data and data.get("is_payroll_locked", False))}
