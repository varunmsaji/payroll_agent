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

# ✅ IMPORT WORKFLOW ENGINE
from app.database import workflow_database as workflow_db

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
# 2️⃣ LEAVE BALANCE
# ============================================================

@router.post("/balance/init")
def initialize_balance(req: Dict[str, Any]):
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
        return {"message": "Leave type already assigned for this year"}

    return res


@router.get("/balance/{employee_id}/{year}")
def get_balance(employee_id: int, year: int):
    return LeaveBalanceDB.get_balance(employee_id, year)


# ============================================================
# 3️⃣ ✅ LEAVE APPLY (AUTO STARTS WORKFLOW)
# ============================================================

@router.post("/apply")
def apply_leave(req: Dict[str, Any]):

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

    year = date.fromisoformat(start_date).year

    # ✅ Balance Check
    balance = LeaveBalanceDB.get_single_balance(employee_id, leave_type_id, year)
    if balance is None:
        raise HTTPException(400, "This leave type is not assigned to this employee for this year")

    # ✅ Overlap Check
    if LeaveRequestDB.has_overlapping_approved_leave(employee_id, start_date, end_date):
        raise HTTPException(400, "Overlapping approved leave exists")

    # ✅ Create Leave
    res = LeaveRequestDB.apply_leave(
        employee_id,
        leave_type_id,
        start_date,
        end_date,
        total_days,
        reason
    )

    # ✅ AUTO START WORKFLOW
    wf = workflow_db.get_active_workflow("leave")
    if wf:
        workflow_db.start_workflow(
            module="leave",
            request_id=res["leave_id"],
            workflow_id=wf["id"],
            employee_id=employee_id
        )

    return {"message": "Leave applied successfully", "data": res}


# ============================================================
# 4️⃣ REQUEST LISTING
# ============================================================

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
# ❌ OLD MANUAL APPROVAL APIS REMOVED
# Workflow Now Controls Approval
# ============================================================


# ============================================================
# 5️⃣ LEAVE HISTORY
# ============================================================

@router.get("/history/{employee_id}")
def get_leave_history(employee_id: int):
    return LeaveHistoryDB.get_history(employee_id)


# ============================================================
# 6️⃣ SALARY BASED ON LEAVES
# ============================================================

@router.get("/salary/{employee_id}/{year}/{month}")
def calculate_salary_after_leaves(employee_id: int, year: int, month: int):

    emp_row = EmployeeSalaryDB.get_base_salary(employee_id)
    if not emp_row or emp_row.get("base_salary") is None:
        raise HTTPException(404, "Employee or base salary not found")

    base_salary = float(emp_row["base_salary"])

    unpaid_days = LeaveHistoryDB.get_unpaid_leave_days(employee_id, year, month)
    unpaid_days = max(unpaid_days, 0)

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
