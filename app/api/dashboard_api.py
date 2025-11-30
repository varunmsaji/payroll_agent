from fastapi import APIRouter
from datetime import date
from app.database.connection import get_connection

router = APIRouter(prefix="/hrms/admin/dashboard", tags=["Admin Dashboard"])


# ------------------------------------------------------------
# ✅ Helper
# ------------------------------------------------------------
def fetch_one(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def fetch_all(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ------------------------------------------------------------
# ✅ ✅ ✅ SINGLE DASHBOARD API (FRONTEND LOADS THIS ONLY)
# ------------------------------------------------------------
@router.get("/overview")
def dashboard_overview():
    today = date.today()

    # --------------------------------------------------------
    # ✅ EMPLOYEE COUNTS
    # --------------------------------------------------------
    emp_sql = """
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'active') AS active
        FROM employees;
    """
    emp = fetch_one(emp_sql)

    # --------------------------------------------------------
    # ✅ TODAY ATTENDANCE SUMMARY (CORRECT)
    # --------------------------------------------------------
    attendance_sql = """
        SELECT
            COUNT(*) FILTER (WHERE status = 'present') AS present,
            COUNT(*) FILTER (WHERE status = 'absent') AS absent,
            COUNT(*) FILTER (WHERE is_late = TRUE) AS late
        FROM attendance
        WHERE date = %s;
    """
    att = fetch_one(attendance_sql, (today,))

    # --------------------------------------------------------
    # ✅ TOTAL OVERTIME (FROM STORED overtime_minutes)
    # --------------------------------------------------------
    overtime_sql = """
        SELECT 
            COALESCE(SUM(overtime_minutes), 0) / 60.0 AS total_overtime_hours
        FROM attendance
        WHERE date = %s;
    """
    overtime = fetch_one(overtime_sql, (today,))

    # --------------------------------------------------------
    # ✅ SHIFT DISTRIBUTION
    # --------------------------------------------------------
    shift_sql = """
        SELECT 
            s.shift_name,
            COUNT(*) AS employees_assigned
        FROM employee_shifts es
        JOIN shifts s ON s.shift_id = es.shift_id
        GROUP BY s.shift_name
        ORDER BY employees_assigned DESC;
    """
    shifts = fetch_all(shift_sql)

    # --------------------------------------------------------
    # ✅ RECENT ATTENDANCE EVENTS (LIVE FEED)
    # --------------------------------------------------------
    events_sql = """
        SELECT 
            e.employee_id,
            e.first_name || ' ' || e.last_name AS employee_name,
            ae.event_type,
            ae.event_time,
            ae.source
        FROM attendance_events ae
        JOIN employees e ON e.employee_id = ae.employee_id
        ORDER BY ae.event_time DESC
        LIMIT 50;
    """
    events = fetch_all(events_sql)

    return {
        "date": today,

        "employees": {
            "total": emp[0],
            "active": emp[1]
        },

        "attendance_today": {
            "present": att[0] or 0,
            "absent": att[1] or 0,
            "late": att[2] or 0
        },

        "overtime_today_hours": round(overtime[0] or 0, 2),

        "shift_distribution": [
            {
                "shift_name": row[0],
                "employees_assigned": row[1]
            } for row in shifts
        ],

        "recent_activity": [
            {
                "employee_id": row[0],
                "employee_name": row[1],
                "event_type": row[2],
                "event_time": row[3],
                "source": row[4]
            } for row in events
        ]
    }
