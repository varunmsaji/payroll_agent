from fastapi import APIRouter, HTTPException
from datetime import date
from typing import Dict, Any

from app.database.leave_database import (
    LeaveTypeDB,
    LeaveBalanceDB,
    LeaveRequestDB,
    LeaveHistoryDB,
    EmployeeSalaryDB,
)

router = APIRouter(prefix="/hrms/leaves", tags=["Leaves"])


# ============================================================
# 1️⃣ LEAVE TYPES CRUD
# ============================================================

@router.post("/types")
def add_leave_type(req: Dict[str, Any]):
    return LeaveTypeDB.add_leave_type(
        req["name"],
        req["code"],
        req.get("yearly_quota", 0),
        req.get("is_paid", True),
        req.get("carry_forward", True)
    )


@router.get("/types")
def get_leave_types():
    return LeaveTypeDB.get_leave_types()


# ============================================================
# 2️⃣ LEAVE BALANCE (Assign leave types to employees)
# ============================================================

@router.post("/balance/init")
def initialize_balance(req: Dict[str, Any]):
    """
    Assign a leave type to an employee for a given year.
    """
    if not all(k in req for k in ("employee_id", "leave_type_id", "year", "quota")):
        raise HTTPException(400, "employee_id, leave_type_id, year, quota are required")

    res = LeaveBalanceDB.initialize_balance(
        req["employee_id"],
        req["leave_type_id"],
        req["year"],
        req["quota"],
        req.get("carry_forwarded", 0)
    )

    if res is None:
        # ON CONFLICT DO NOTHING triggered
        return {"message": "Leave type already assigned for this year"}

    return res


@router.get("/balance/{employee_id}/{year}")
def get_balance(employee_id: int, year: int):
    return LeaveBalanceDB.get_balance(employee_id, year)


# ============================================================
# 3️⃣ LEAVE REQUESTS - APPLY / LIST
# ============================================================

@router.post("/apply")
def apply_leave(req: Dict[str, Any]):
    """
    Apply for leave with validation:
    - check leave type assigned to employee
    - check no overlapping approved leave
    - (optional) check total_days > 0
    """
    required = ["employee_id", "leave_type_id", "start_date", "end_date", "total_days"]
    for key in required:
        if key not in req:
            raise HTTPException(400, f"{key} is required")

    employee_id = req["employee_id"]
    leave_type_id = req["leave_type_id"]
    start_date = req["start_date"]
    end_date = req["end_date"]
    total_days = float(req["total_days"])
    reason = req.get("reason", "")

    if total_days <= 0:
        raise HTTPException(400, "total_days must be > 0")

    # year for balance
    year = date.fromisoformat(start_date).year

    # 1. Check if employee has this leave type assigned
    balance = LeaveBalanceDB.get_single_balance(employee_id, leave_type_id, year)
    if balance is None:
        raise HTTPException(400, "This leave type is not assigned to this employee for this year")

    # 2. Check for overlapping APPROVED leaves
    if LeaveRequestDB.has_overlapping_approved_leave(employee_id, start_date, end_date):
        raise HTTPException(400, "Overlapping approved leave exists for this period")

    # (We do NOT deduct balance yet; balance is updated on approval)
    res = LeaveRequestDB.apply_leave(
        employee_id,
        leave_type_id,
        start_date,
        end_date,
        total_days,
        reason
    )

    return {"message": "Leave applied successfully", "data": res}


@router.get("/requests")
def get_all_requests():
    return LeaveRequestDB.list_requests()


@router.get("/requests/pending")
def get_pending_requests():
    return LeaveRequestDB.list_pending_requests()


@router.get("/requests/{employee_id}")
def get_employee_requests(employee_id: int):
    return LeaveRequestDB.list_requests(employee_id)


# ============================================================
# 4️⃣ LEAVE APPROVAL / REJECTION
# ============================================================

@router.post("/approve/{leave_id}")
def approve_leave(leave_id: int, req: Dict[str, Any]):
    if "manager_id" not in req:
        raise HTTPException(400, "manager_id is required")

    manager_id = req["manager_id"]

    try:
        result = LeaveRequestDB.approve_leave_transaction(leave_id, manager_id)
        return {"message": "Leave approved", "data": result}
    except Exception as e:
        # Map business errors to HTTP
        raise HTTPException(400, str(e))


@router.post("/reject/{leave_id}")
def reject_leave(leave_id: int, req: Dict[str, Any]):
    if "manager_id" not in req:
        raise HTTPException(400, "manager_id is required")

    res = LeaveRequestDB.reject_leave(leave_id, req["manager_id"])
    if not res:
        raise HTTPException(404, "Leave request not found")

    return {"message": "Leave rejected", "data": res}


# ============================================================
# 5️⃣ LEAVE HISTORY
# ============================================================

@router.get("/history/{employee_id}")
def get_leave_history(employee_id: int):
    return LeaveHistoryDB.get_history(employee_id)


# ============================================================
# 6️⃣ SALARY CALCULATION BASED ON LEAVES
# ============================================================

@router.get("/salary/{employee_id}/{year}/{month}")
def calculate_salary_after_leaves(employee_id: int, year: int, month: int):
    """
    Calculates final salary based on:
    - base_salary from employees table
    - unpaid leave days in leave_history (where leave_types.is_paid = FALSE)

    Simple formula:
        daily_salary = base_salary / 30
        deduction    = unpaid_days * daily_salary
        final_salary = base_salary - deduction
    """

    # 1. Base salary
    emp_row = EmployeeSalaryDB.get_base_salary(employee_id)
    if not emp_row or emp_row.get("base_salary") is None:
        raise HTTPException(404, "Employee or base salary not found")

    base_salary = float(emp_row["base_salary"])

    # 2. Unpaid leave days
    unpaid_days = LeaveHistoryDB.get_unpaid_leave_days(employee_id, year, month)

    if unpaid_days < 0:
        unpaid_days = 0

    # 3. Salary calculation
    daily_salary = base_salary / 30.0
    deduction = unpaid_days * daily_salary
    final_salary = base_salary - deduction

    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "base_salary": base_salary,
        "unpaid_leave_days": unpaid_days,
        "daily_salary": daily_salary,
        "deduction": deduction,
        "final_salary": final_salary
    }
