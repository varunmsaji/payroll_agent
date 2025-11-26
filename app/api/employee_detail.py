from fastapi import APIRouter
from datetime import date, datetime, timedelta
from typing import Dict, Any

# Import all database classes
# from app.database.database_functions import (
#     EmployeeDB,
#     ShiftDB,
#     EmployeeShiftDB,
#     AttendanceEventDB,
#     AttendanceDB,
#     SalaryDB,
#     PayrollDB
# )
from app.database.attendence import AttendanceDB,AttendanceEventDB
from app.database.employee_db import EmployeeDB
from app.database.employee_shift_db import EmployeeShiftDB
from app.database.salary import SalaryDB
from app.database.payroll import PayrollDB

router = APIRouter(prefix="/hrms", tags=["Employee Details"])



# ============================================================
# 1️⃣ EMPLOYEE BASIC PROFILE
# ============================================================
@router.get("/employee/{employee_id}")
def employee_profile(employee_id: int):
    emp = EmployeeDB.get_employee(employee_id)
    if not emp:
        return {"error": "Employee not found"}
    return emp



# ============================================================
# 2️⃣ CURRENT SHIFT DETAILS
# ============================================================
@router.get("/employee/{employee_id}/shift")
def employee_shift(employee_id: int):
    return EmployeeShiftDB.get_current_shift(employee_id)



# ============================================================
# 3️⃣ ATTENDANCE SUMMARY (today + last 7 + last 30 days)
# ============================================================
@router.get("/employee/{employee_id}/attendance-summary")
def attendance_summary(employee_id: int):
    all_att = AttendanceDB.get_attendance(employee_id)

    today = date.today()

    today_record = next((a for a in all_att if a["date"] == today), None)

    # last 7 & last 30 entries
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
    ).seconds / 3600  # float

    late_count = 0
    overtime_hours = 0.0

    for a in last_30:
        # Convert DB Decimal → float
        total_hours = float(a["total_hours"]) if a["total_hours"] else 0

        # LATE
        if a["check_in"] and a["check_in"].time() > shift_start:
            late_count += 1

        # OVERTIME
        if total_hours > shift_duration_hours:
            overtime_hours += total_hours - shift_duration_hours

    return {
        "late_days_last_30_days": late_count,
        "overtime_hours_last_30_days": round(overtime_hours, 2),
    }



# ============================================================
# 5️⃣ RECENT ATTENDANCE EVENTS (last 20)
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
# 9️⃣ OPTIONAL → COMBINED DETAILS API (single request)
# ============================================================
@router.get("/employee/{employee_id}/full-details")
def full_employee_details(employee_id: int):
    return {
        "profile": EmployeeDB.get_one(employee_id),  # ✅ FIXED
        "shift": EmployeeShiftDB.get_current_shift(employee_id),
        "attendance_summary": attendance_summary(employee_id),
        "time_summary": time_summary(employee_id),
        "events": employee_events(employee_id),
        "salary_structure": employee_salary(employee_id),
        "latest_payroll": latest_payroll(employee_id),
        "payroll_history": payroll_history(employee_id)
    }


@router.get("/employees")
def get_employees():
    return EmployeeDB.get_all()

