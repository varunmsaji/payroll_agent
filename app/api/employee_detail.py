from fastapi import APIRouter, HTTPException
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.database.attendence import AttendanceDB, AttendanceEventDB
from app.database.employee_db import EmployeeDB
from app.database.employee_shift_db import EmployeeShiftDB
from app.database.salary import SalaryDB
from app.database.payroll import PayrollDB

router = APIRouter(prefix="/hrms", tags=["Employee Details"])


# ============================================================
# ✅ MANAGER SCHEMA
# ============================================================
class ManagerUpdate(BaseModel):
    manager_id: Optional[int] = None


# ============================================================
# 1️⃣ EMPLOYEE BASIC PROFILE (WITH MANAGER)
# ============================================================
@router.get("/employee/{employee_id}")
def employee_profile(employee_id: int):
    emp = EmployeeDB.get_one(employee_id)
    if not emp:
        return {"error": "Employee not found"}
    return emp


# ============================================================
# ✅ 1.1 GET ALL EMPLOYEES (WITH MANAGER NAMES)
# ============================================================
@router.get("/employees")
def get_employees():
    """
    Used by:
    - Admin panel
    - Manager assignment page
    - Org chart
    """
    return EmployeeDB.get_all()


# ============================================================
# ✅ 1.2 GET ALL MANAGERS (FOR DROPDOWNS)
# ============================================================
@router.get("/employees/managers")
def get_managers():
    """
    Used in:
    - Manager assignment dropdown
    - Workflow assignment UI
    """
    return EmployeeDB.get_all_managers()


# ============================================================
# ✅ 1.3 ASSIGN / CHANGE MANAGER (ADMIN)
# ============================================================
@router.put("/employee/{employee_id}/manager")
def assign_manager(employee_id: int, req: ManagerUpdate):

    # Prevent self-manager
    if req.manager_id == employee_id:
        raise HTTPException(
            status_code=400,
            detail="An employee cannot be their own manager"
        )

    # Check employee exists
    emp = EmployeeDB.get_one(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # If assigning manager, validate manager exists
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
# 2️⃣ CURRENT SHIFT DETAILS
# ============================================================
@router.get("/employee/{employee_id}/shift")
def employee_shift(employee_id: int):
    return EmployeeShiftDB.get_current_shift(employee_id)


# ============================================================
# 3️⃣ ATTENDANCE SUMMARY
# ============================================================
@router.get("/employee/{employee_id}/attendance-summary")
def attendance_summary(employee_id: int):
    all_att = AttendanceDB.get_attendance(employee_id)

    today = date.today()
    today_record = next((a for a in all_att if a["date"] == today), None)

    last_7 = all_att[:7]
    last_30 = all_att[:30]

    total_hours_30 = sum((a["total_hours"] or 0) for a in last_30)

    return {
        "today": today_record,
        "last_7_days": last_7,
        "last_30_days": last_30,
        "total_hours_last_30_days": total_hours_30,
    }


# ============================================================
# 4️⃣ LATE + OVERTIME SUMMARY
# ============================================================
@router.get("/employee/{employee_id}/time-summary")
def time_summary(employee_id: int):
    shift = EmployeeShiftDB.get_current_shift(employee_id)
    if not shift:
        return {"error": "Shift not assigned"}

    all_att = AttendanceDB.get_attendance(employee_id)
    last_30 = all_att[:30]

    shift_start = shift["start_time"]
    shift_end = shift["end_time"]

    shift_duration_hours = (
        datetime.combine(date.today(), shift_end) -
        datetime.combine(date.today(), shift_start)
    ).seconds / 3600

    late_count = 0
    overtime_hours = 0.0

    for a in last_30:
        total_hours = float(a["total_hours"]) if a["total_hours"] else 0

        if a["check_in"] and a["check_in"].time() > shift_start:
            late_count += 1

        if total_hours > shift_duration_hours:
            overtime_hours += total_hours - shift_duration_hours

    return {
        "late_days_last_30_days": late_count,
        "overtime_hours_last_30_days": round(overtime_hours, 2),
    }


# ============================================================
# 5️⃣ RECENT ATTENDANCE EVENTS
# ============================================================
@router.get("/employee/{employee_id}/events")
def employee_events(employee_id: int):
    events = AttendanceEventDB.get_all_events_for_employee(employee_id)
    return events[:20]


# ============================================================
# 6️⃣ SALARY STRUCTURE
# ============================================================
@router.get("/employee/{employee_id}/salary")
def employee_salary(employee_id: int):
    return SalaryDB.get_salary_structure(employee_id)


# ============================================================
# 7️⃣ LATEST PAYROLL DETAILS
# ============================================================
@router.get("/employee/{employee_id}/payroll/latest")
def latest_payroll(employee_id: int):
    today = date.today()
    return PayrollDB.get_payroll(employee_id, today.month, today.year)


# ============================================================
# 8️⃣ PAYROLL HISTORY (last 6 months)
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
# 9️⃣ FULL EMPLOYEE DASHBOARD
# ============================================================
@router.get("/employee/{employee_id}/full-details")
def full_employee_details(employee_id: int):
    return {
        "profile": EmployeeDB.get_one(employee_id),
        "shift": EmployeeShiftDB.get_current_shift(employee_id),
        "attendance_summary": attendance_summary(employee_id),
        "time_summary": time_summary(employee_id),
        "events": employee_events(employee_id),
        "salary_structure": employee_salary(employee_id),
        "latest_payroll": latest_payroll(employee_id),
        "payroll_history": payroll_history(employee_id)
    }
