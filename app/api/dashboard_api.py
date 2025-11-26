from fastapi import APIRouter
from datetime import date
from app.database.database import get_connection   # your DB connector

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ------------------------------------------------------------
# Helper function
# ------------------------------------------------------------
def fetch(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ------------------------------------------------------------
# 1️⃣ Total Employees & Active Employees
# ------------------------------------------------------------
@router.get("/employees-summary")
def employees_summary():
    sql = """
        SELECT 
            (SELECT COUNT(*) FROM employees) AS total_employees,
            (SELECT COUNT(*) FROM employees WHERE status='active') AS active_employees
    """
    return fetch(sql)[0]


# ------------------------------------------------------------
# 2️⃣ Today's Attendance Summary (Present, Absent)
# ------------------------------------------------------------
@router.get("/attendance-today")
def attendance_today():
    today = date.today()

    sql = """
        SELECT
            (SELECT COUNT(*) FROM attendance WHERE date=%s) AS present,
            (SELECT COUNT(*) FROM employees) 
                - (SELECT COUNT(*) FROM attendance WHERE date=%s) AS absent
    """
    return fetch(sql, (today, today))[0]


# ------------------------------------------------------------
# 3️⃣ Late vs On-time vs Absent
# ------------------------------------------------------------
@router.get("/late-on-time-absent")
def late_ontime_absent():
    today = date.today()

    sql = """
        SELECT
            COUNT(*) FILTER (WHERE a.check_in::time > s.start_time) AS late,
            COUNT(*) FILTER (WHERE a.check_in::time <= s.start_time) AS on_time,
            (
                SELECT COUNT(*) FROM employees 
                WHERE employee_id NOT IN (SELECT employee_id FROM attendance WHERE date=%s)
            ) AS absent
        FROM attendance a
        JOIN employee_shifts es ON es.employee_id = a.employee_id
        JOIN shifts s ON s.shift_id = es.shift_id
        WHERE a.date=%s
    """
    return fetch(sql, (today, today))[0]


# ------------------------------------------------------------
# 4️⃣ Overtime totals (Total overtime hours today)
# ------------------------------------------------------------
@router.get("/overtime-today")
def overtime_today():
    today = date.today()

    sql = """
        SELECT 
            SUM(
                a.total_hours - (EXTRACT(EPOCH FROM (s.end_time - s.start_time)) / 3600)
            ) AS total_overtime_hours
        FROM attendance a
        JOIN employee_shifts es ON es.employee_id = a.employee_id
        JOIN shifts s ON s.shift_id = es.shift_id
        WHERE a.date=%s
          AND a.total_hours > (EXTRACT(EPOCH FROM (s.end_time - s.start_time)) / 3600)
    """
    row = fetch(sql, (today,))[0]
    return row


# ------------------------------------------------------------
# 5️⃣ Monthly Payroll Summary
# ------------------------------------------------------------
@router.get("/payroll-summary/{month}/{year}")
def payroll_summary(month: int, year: int):
    sql = """
        SELECT
            SUM(gross_salary) AS total_gross,
            SUM(net_salary) AS total_net,
            COUNT(*) AS employees_paid,
            AVG(net_salary) AS avg_salary
        FROM payroll
        WHERE month=%s AND year=%s
    """
    return fetch(sql, (month, year))[0]


# ------------------------------------------------------------
# 6️⃣ Monthly Working Hours Summary
# ------------------------------------------------------------
@router.get("/monthly-hours/{month}/{year}")
def monthly_hours(month: int, year: int):
    sql = """
        SELECT 
            employee_id,
            SUM(total_hours) AS monthly_hours
        FROM attendance
        WHERE EXTRACT(MONTH FROM date)=%s
          AND EXTRACT(YEAR FROM date)=%s
        GROUP BY employee_id
        ORDER BY monthly_hours DESC
    """
    return fetch(sql, (month, year))


# ------------------------------------------------------------
# 7️⃣ Recent Attendance Events (last 50)
# ------------------------------------------------------------
@router.get("/recent-events")
def recent_events():
    sql = """
        SELECT 
            e.first_name || ' ' || e.last_name AS employee,
            a.event_type,
            a.event_time,
            a.source
        FROM attendance_events a
        JOIN employees e ON e.employee_id = a.employee_id
        ORDER BY a.event_time DESC
        LIMIT 50
    """
    return fetch(sql)


# ------------------------------------------------------------
# 8️⃣ Shift-wise employee distribution
# ------------------------------------------------------------
@router.get("/shift-distribution")
def shift_distribution():
    sql = """
        SELECT 
            s.shift_name,
            COUNT(*) AS employees_assigned
        FROM employee_shifts es
        JOIN shifts s ON s.shift_id = es.shift_id
        GROUP BY s.shift_name
        ORDER BY employees_assigned DESC
    """
    return fetch(sql)
