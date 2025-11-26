from fastapi import APIRouter
from datetime import date
from app.database.attendence import  AttendanceDB, EmployeeShiftDB
from app.database.employee_db import EmployeeDB
from app.database.shifts_db import ShiftDB
router = APIRouter(prefix="/hrms", tags=["Dashboard Stats"])


# ============================================================
# 🔹 1. GLOBAL ATTENDANCE STATS (Today)
# ============================================================
@router.get("/dashboard/today-stats")
def today_stats():
    today = date.today()

    employees = EmployeeDB.get_all()
    total_employees = len(employees)

    # Get today's attendance
    today_att = []
    for emp in employees:
        att = AttendanceDB.get_attendance(emp["employee_id"])
        if att and att[0]["date"] == today:
            today_att.append(att[0])

    present_today = len(today_att)
    absent_today = total_employees - present_today

    late_today = sum(1 for a in today_att if a["late_minutes"] > 0)
    overtime_today = sum(a["overtime_minutes"] for a in today_att) / 60
    total_hours_today = sum(a["total_hours"] for a in today_att)

    # Shift-wise counts
    shift_map = {}
    for a in today_att:
        shift = EmployeeShiftDB.get_current_shift(a["employee_id"])
        if shift:
            name = shift["shift_name"]
            shift_map[name] = shift_map.get(name, 0) + 1

    shift_list = [{"shift_name": k, "count": v} for k, v in shift_map.items()]

    return {
        "total_employees": total_employees,
        "present_today": present_today,
        "absent_today": absent_today,
        "late_today": late_today,
        "overtime_today": round(overtime_today, 2),
        "total_hours_today": round(total_hours_today, 2),
        "shift_wise": shift_list
    }


# ============================================================
# 🔹 2. EMPLOYEE-WISE TODAY ATTENDANCE TABLE
# ============================================================
@router.get("/attendance/today")
def today_attendance_table():
    today = date.today()
    employees = EmployeeDB.get_all()
    final_list = []

    for emp in employees:
        att_list = AttendanceDB.get_attendance(emp["employee_id"])

        # No attendance today
        if not att_list or att_list[0]["date"] != today:
            continue

        att = att_list[0]

        # Get shift
        shift = EmployeeShiftDB.get_current_shift(emp["employee_id"])
        shift_name = shift["shift_name"] if shift else None

        final_list.append({
            "employee_id": emp["employee_id"],
            "name": f"{emp['first_name']} {emp['last_name']}",
            "shift": shift_name,
            "check_in": att["check_in"],
            "check_out": att["check_out"],
            "total_hours": att["total_hours"],
            "late_minutes": att["late_minutes"],
            "overtime_minutes": att["overtime_minutes"]
        })

    return final_list
