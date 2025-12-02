from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from psycopg2.extras import RealDictCursor

from app.database.connection import get_connection
from app.database.payroll import PayrollPolicyDB

# ✅ IMPORT YOUR REAL WORKFLOW DATABASE
from app.database import workflow_database as workflow_db

router = APIRouter(prefix="/hrms/settings", tags=["Settings"])


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
# ✅ ATTENDANCE POLICY MODELS
# ============================================================

class AttendancePolicyUpdate(BaseModel):
    late_grace_minutes: int
    early_exit_grace_minutes: int
    full_day_fraction: float
    half_day_fraction: float
    night_shift_enabled: bool
    overtime_enabled: bool


# ============================================================
# ✅ PAYROLL POLICY SETTINGS
# ============================================================

@router.get("/payroll-policy")
def get_payroll_policy():
    policy = PayrollPolicyDB.get_active_policy()
    if not policy:
        raise HTTPException(status_code=404, detail="No payroll policy found")
    return policy


@router.put("/payroll-policy")
def update_payroll_policy(payload: PayrollPolicyUpdate):
    policy = PayrollPolicyDB.update_policy(payload.dict())
    return {
        "message": "Payroll policy updated successfully",
        "policy": policy
    }


# ============================================================
# ✅ ATTENDANCE POLICY SETTINGS (DYNAMIC)
# ============================================================

@router.get("/attendance-policy")
def get_attendance_policy():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM attendance_policies
        WHERE active = TRUE
        ORDER BY created_at DESC
        LIMIT 1;
    """)

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No attendance policy found")

    return row


@router.put("/attendance-policy")
def update_attendance_policy(payload: AttendancePolicyUpdate):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("UPDATE attendance_policies SET active = FALSE;")

    cur.execute("""
        INSERT INTO attendance_policies (
            late_grace_minutes,
            early_exit_grace_minutes,
            full_day_fraction,
            half_day_fraction,
            night_shift_enabled,
            overtime_enabled,
            active
        )
        VALUES (%s,%s,%s,%s,%s,%s,TRUE)
        RETURNING *;
    """, (
        payload.late_grace_minutes,
        payload.early_exit_grace_minutes,
        payload.full_day_fraction,
        payload.half_day_fraction,
        payload.night_shift_enabled,
        payload.overtime_enabled
    ))

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "message": "Attendance policy updated",
        "policy": row
    }


# ============================================================
# ✅ WORKFLOW SETTINGS (SAFE VERSION)
# ============================================================

@router.get("/workflows")
def list_workflows():
    try:
        # ✅ Most workflow DBs have this
        workflows = workflow_db.get_all_workflows()
        return workflows
    except:
        # ✅ Safe fallback if function names differ
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM workflows
            ORDER BY created_at DESC;
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return rows


@router.post("/workflows/activate")
def activate_workflow(payload: Dict[str, Any]):
    workflow_id = payload.get("workflow_id")
    if not workflow_id:
        raise HTTPException(400, "workflow_id is required")

    workflow_db.activate_workflow(workflow_id)

    return {
        "message": f"Workflow {workflow_id} activated successfully"
    }


@router.post("/workflows/deactivate")
def deactivate_workflow(payload: Dict[str, Any]):
    workflow_id = payload.get("workflow_id")
    if not workflow_id:
        raise HTTPException(400, "workflow_id is required")

    workflow_db.deactivate_workflow(workflow_id)

    return {
        "message": f"Workflow {workflow_id} deactivated successfully"
    }
