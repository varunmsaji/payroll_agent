from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, constr

from app.database.attendence import AttendanceDB, AttendanceEventDB
from app.database.employee_db import EmployeeDB
from app.database.employee_shift_db import EmployeeShiftDB
from app.database.salary import SalaryDB
from app.database.payroll import PayrollDB
from app.database.connection import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/hrms", tags=["Employee Details"])


# ============================================================
# ✅ SCHEMAS (VALIDATION ADDED)
# ============================================================

class ManagerUpdate(BaseModel):
    manager_id: Optional[int] = None


# ============================================================
# ✅ 1️⃣ EMPLOYEE BASIC PROFILE
# ============================================================
@router.get("/employee/{employee_id}")
def employee_profile(employee_id: int):
    emp = EmployeeDB.get_one(employee_id)

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return emp


# ============================================================
# ✅ 1.1 GET ALL EMPLOYEES (WITH PAGINATION ✅)
# ============================================================
@router.get("/employees")
def get_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    ✅ Production safe with pagination.
    """
    employees = EmployeeDB.get_all()

    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total": len(employees),
        "data": employees[start:end]
    }


# ============================================================
# ✅ 1.2 GET ALL MANAGERS
# ============================================================
@router.get("/employees/managers")
def get_managers():
    return EmployeeDB.get_all_managers()


# ============================================================
# ✅ 1.3 ASSIGN / CHANGE MANAGER (STRONG VALIDATION ✅)
# ============================================================
@router.put("/employee/{employee_id}/manager")
def assign_manager(employee_id: int, req: ManagerUpdate):

    if req.manager_id == employee_id:
        raise HTTPException(status_code=400, detail="Employee cannot be their own manager")

    emp = EmployeeDB.get_one(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if req.manager_id:
        mgr = EmployeeDB.get_one(req.manager_id)
        if not mgr:
            raise HTTPException(status_code=404, detail="Manager not found")

    updated = EmployeeDB.set_manager(employee_id, req.manager_id)

    return {
        "message": "Manager assigned successfully",
        "employee": updated
    }


# ============================================================
# ✅ 2️⃣ CURRENT SHIFT DETAILS (SAFE ✅)
# ============================================================
@router.get("/employee/{employee_id}/shift")
def employee_shift(employee_id: int):
    shift = EmployeeShiftDB.get_current_shift(employee_id)
    if not shift:
        return {"message": "No active shift assigned"}
    return shift


# ============================================================
# ✅ 3️⃣ ATTENDANCE SUMMARY
# ============================================================
@router.get("/employee/{employee_id}/attendance-summary")
def attendance_summary(employee_id: int):
    all_att = AttendanceDB.get_attendance(employee_id)

    today = date.today()
    today_record = next((a for a in all_att if a["date"] == today), None)

    last_7 = all_att[:7]
    last_30 = all_att[:30]

    total_hours_30 = sum(float(a["total_hours"] or 0) for a in last_30)

    return {
        "today": today_record,
        "last_7_days": last_7,
        "last_30_days": last_30,
        "total_hours_last_30_days": round(total_hours_30, 2),
    }


# ============================================================
# ✅ 4️⃣ LATE + OVERTIME SUMMARY (SAFE ✅)
# ============================================================
@router.get("/employee/{employee_id}/time-summary")
def time_summary(employee_id: int):
    shift = EmployeeShiftDB.get_current_shift(employee_id)
    if not shift:
        return {"message": "Shift not assigned"}

    all_att = AttendanceDB.get_attendance(employee_id)
    last_30 = all_att[:30]

    shift_start = shift["start_time"]
    shift_end = shift["end_time"]

    shift_duration_hours = (
        datetime.combine(date.today(), shift_end)
        - datetime.combine(date.today(), shift_start)
    ).seconds / 3600

    late_count = 0
    overtime_hours = 0.0

    for a in last_30:
        total_hours = float(a["total_hours"] or 0)

        if a["check_in"] and a["check_in"].time() > shift_start:
            late_count += 1

        if total_hours > shift_duration_hours:
            overtime_hours += total_hours - shift_duration_hours

    return {
        "late_days_last_30_days": late_count,
        "overtime_hours_last_30_days": round(overtime_hours, 2),
    }


# ============================================================
# ✅ 5️⃣ RECENT ATTENDANCE EVENTS
# ============================================================
@router.get("/employee/{employee_id}/events")
def employee_events(employee_id: int):
    events = AttendanceEventDB.get_all_events_for_employee(employee_id)
    return events[:20]


# ============================================================
# ✅ 6️⃣ SALARY STRUCTURE
# ============================================================
@router.get("/employee/{employee_id}/salary")
def employee_salary(employee_id: int):
    salary = SalaryDB.get_salary_structure(employee_id)
    if not salary:
        return {"message": "Salary structure not created"}
    return salary


# ============================================================
# ✅ 7️⃣ LATEST PAYROLL
# ============================================================
@router.get("/employee/{employee_id}/payroll/latest")
def latest_payroll(employee_id: int):
    today = date.today()
    payroll = PayrollDB.get_payroll(employee_id, today.month, today.year)
    if not payroll:
        return {"message": "Payroll not generated yet"}
    return payroll


# ============================================================
# ✅ 8️⃣ PAYROLL HISTORY (6 MONTHS ✅)
# ============================================================
@router.get("/employee/{employee_id}/payroll-history")
def payroll_history(employee_id: int):
    today = date.today()
    history = []

    for i in range(6):
        month = today.month - i
        year = today.year

        if month <= 0:
            month += 12
            year -= 1

        payroll = PayrollDB.get_payroll(employee_id, month, year)
        if payroll:
            history.append(payroll)

    return history


# ============================================================
# ✅ 9️⃣ FULL EMPLOYEE DASHBOARD (SAFE ✅)
# ============================================================
@router.get("/employee/{employee_id}/full-details")
def full_employee_details(employee_id: int):

    emp = EmployeeDB.get_one(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "profile": emp,
        "shift": EmployeeShiftDB.get_current_shift(employee_id),
        "attendance_summary": attendance_summary(employee_id),
        "time_summary": time_summary(employee_id),
        "events": employee_events(employee_id),
        "salary_structure": employee_salary(employee_id),
        "latest_payroll": latest_payroll(employee_id),
        "payroll_history": payroll_history(employee_id)
    }




@router.get("/employees/ui")
def employees_for_ui(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    sql = """
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.department,
            e.designation,
            e.status,
            m.first_name || ' ' || m.last_name AS manager,
            s.shift_name
        FROM employees e
        LEFT JOIN employee_manager em ON em.employee_id = e.employee_id
        LEFT JOIN employees m ON m.employee_id = em.manager_id
        LEFT JOIN employee_shifts es ON es.employee_id = e.employee_id
        LEFT JOIN shifts s ON s.shift_id = es.shift_id
        WHERE 1=1
    """

    params = []

    if search:
        sql += " AND (e.first_name ILIKE %s OR e.last_name ILIKE %s OR e.email ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if department:
        sql += " AND e.department = %s"
        params.append(department)

    if status:
        sql += " AND e.status = %s"
        params.append(status)

    sql += " ORDER BY e.first_name"

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@router.get("/employee/{employee_id}/leaves")
def employee_leaves(employee_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM leave_requests
        WHERE employee_id = %s
        ORDER BY start_date DESC
    """, (employee_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows





@router.get("/payroll/ui-list")
def payroll_ui_list(month: int, year: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            p.employee_id,
            e.first_name || ' ' || e.last_name AS employee,
            p.working_days,
            p.present_days,
            p.gross_salary,
            p.net_salary
        FROM payroll p
        JOIN employees e ON e.employee_id = p.employee_id
        WHERE p.month = %s AND p.year = %s
        ORDER BY e.first_name
    """, (month, year))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ============================================================
# ✅ 10️⃣ EMPLOYEE LEAVE BALANCE (UI FRIENDLY ✅)
# ============================================================
@router.get("/employee/{employee_id}/leave-balance")
def leave_balance(employee_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                lt.name AS leave_type,
                lb.year,
                lb.total_quota,
                lb.used,
                lb.remaining,
                lb.carry_forwarded
            FROM leave_balance lb
            JOIN leave_types lt 
                ON lt.leave_type_id = lb.leave_type_id
            WHERE lb.employee_id = %s
            ORDER BY lb.year DESC, lt.name;
        """, (employee_id,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for row in rows:
            result.append({
                "leave_type": row[0],
                "year": row[1],
                "total_quota": float(row[2]),
                "used": float(row[3]),
                "remaining": float(row[4]),
                "carry_forwarded": float(row[5]),
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
