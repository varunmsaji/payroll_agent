from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
from psycopg2.extras import RealDictCursor

from app.services.payroll_service import PayrollService
from app.database.payroll import PayrollDB
from app.database.payroll import PayrollPolicyDB
from app.database.connection import get_connection

router = APIRouter(prefix="/hrms/payroll", tags=["Payroll"])


# ============================================================
# ✅ PAYROLL POLICY MODELS
# ============================================================

class PayrollPolicyUpdate(BaseModel):
    late_grace_minutes: int
    late_lop_threshold_minutes: int
    early_exit_grace_minutes: int
    early_exit_lop_threshold_minutes: int
    overtime_enabled: bool
    overtime_multiplier: float
    holiday_double_pay: bool
    weekend_paid_only_if_worked: bool
    night_shift_allowance: float


# ============================================================
# ✅ PAYROLL REQUEST MODELS
# ============================================================

class PayrollGenerateRequest(BaseModel):
    employee_id: int
    year: int
    month: int


class PayrollBulkGenerateRequest(BaseModel):
    year: int
    month: int


# ============================================================
# ✅ 0️⃣ GET ACTIVE PAYROLL POLICY ✅✅✅
# ============================================================

@router.get("/policy")
def get_active_policy():
    policy = PayrollPolicyDB.get_active_policy()
    if not policy:
        raise HTTPException(status_code=404, detail="No active payroll policy found")
    return policy


# ============================================================
# ✅ 0️⃣ UPDATE PAYROLL POLICY ✅✅✅ (ADMIN)
# ============================================================

@router.put("/policy")
def update_policy(payload: PayrollPolicyUpdate):
    updated = PayrollPolicyDB.update_policy(payload.dict())
    return updated


# ============================================================
# ✅ 1️⃣ GENERATE PAYROLL FOR ONE EMPLOYEE
# ============================================================

@router.post("/generate")
def generate_payroll(payload: PayrollGenerateRequest):
    try:
        return PayrollService.generate_for_employee(
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ✅ 2️⃣ BULK PAYROLL FOR ALL EMPLOYEES
# ============================================================

@router.post("/generate-bulk")
def generate_bulk_payroll(payload: PayrollBulkGenerateRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT employee_id FROM employees WHERE status = 'active';")
    employees = cur.fetchall()

    cur.close()
    conn.close()

    if not employees:
        raise HTTPException(status_code=404, detail="No active employees found")

    results = []

    for emp in employees:
        emp_id = emp[0]
        try:
            payroll = PayrollService.generate_for_employee(
                employee_id=emp_id,
                year=payload.year,
                month=payload.month
            )
            results.append({
                "employee_id": emp_id,
                "status": "success",
                "payroll": payroll["payroll"]
            })
        except Exception as e:
            results.append({
                "employee_id": emp_id,
                "status": "failed",
                "error": str(e)
            })

    return {
        "year": payload.year,
        "month": payload.month,
        "results": results
    }


# ============================================================
# ✅ 3️⃣ MONTHLY PAYROLL LIST (ADMIN)
# ⚠️ MUST COME BEFORE /{employee_id}
# ============================================================

@router.get("/month/list")
def get_month_payroll(year: int = Query(...), month: int = Query(...)):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT p.*, e.first_name, e.last_name, e.designation
        FROM payroll p
        JOIN employees e ON e.employee_id = p.employee_id
        WHERE p.year = %s AND p.month = %s
        ORDER BY e.first_name;
    """, (year, month))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows


# ============================================================
# ✅ 4️⃣ GET PAYROLL FOR SINGLE EMPLOYEE
# ============================================================

@router.get("/{employee_id}")
def get_employee_payroll(
    employee_id: int,
    year: int = Query(...),
    month: int = Query(...)
):
    payroll = PayrollDB.get_payroll(employee_id, month, year)
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    return payroll


# ============================================================
# ✅ 5️⃣ REGENERATE PAYROLL (ADMIN OVERRIDE)
# ============================================================

@router.post("/regenerate")
def regenerate_payroll(payload: PayrollGenerateRequest):
    try:
        return PayrollService.generate_for_employee(
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ✅ 6️⃣ PAYROLL STATUS CHECK
# ============================================================

@router.get("/status/{employee_id}")
def payroll_status(
    employee_id: int,
    year: int = Query(...),
    month: int = Query(...)
):
    payroll = PayrollDB.get_payroll(employee_id, month, year)

    if payroll:
        return {
            "employee_id": employee_id,
            "year": year,
            "month": month,
            "status": "generated",
            "payroll_id": payroll["payroll_id"]
        }

    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "status": "not_generated"
    }
