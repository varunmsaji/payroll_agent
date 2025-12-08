from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import time, date, timedelta
from psycopg2.extras import RealDictCursor

from app.database.shifts_db import ShiftDB
from app.database.connection import get_connection
from app.database.employee_db import EmployeeDB
from app.database.employee_shift_db import EmployeeShiftDB

router = APIRouter(prefix="/hrms/shifts", tags=["Shifts"])

# ============================================================
# 🧱 SCHEMAS
# ============================================================

class ShiftBase(BaseModel):
    shift_name: str
    start_time: time
    end_time: time
    is_night_shift: bool = False
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    break_minutes: int = 0


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(ShiftBase):
    pass


class ShiftAssignRequest(BaseModel):
    employee_id: int
    shift_id: int
    effective_from: date

# ============================================================
# 1️⃣ LIST SHIFTS (ADMIN TABLE)
# ============================================================

@router.get("/")
def list_shifts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False)
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if include_inactive:
        cur.execute("SELECT COUNT(*) AS count FROM shifts;")
    else:
        cur.execute("SELECT COUNT(*) AS count FROM shifts WHERE is_active = true;")
    
    total = cur.fetchone()["count"]
    offset = (page - 1) * limit

    if include_inactive:
        cur.execute("""
            SELECT * FROM shifts
            ORDER BY shift_id DESC
            LIMIT %s OFFSET %s;
        """, (limit, offset))
    else:
        cur.execute("""
            SELECT * FROM shifts
            WHERE is_active = true
            ORDER BY shift_id DESC
            LIMIT %s OFFSET %s;
        """, (limit, offset))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"page": page, "limit": limit, "total": total, "data": rows}

# ============================================================
# ✅ ✅ ✅ 2️⃣ SHIFT ROSTER (✅ MUST BE BEFORE /{shift_id})
# ============================================================

@router.get("/roster")
def roster(date_: date = Query(default=date.today())):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.department,
            e.designation,
            s.shift_id,
            s.shift_name,
            s.start_time,
            s.end_time,
            es.effective_from,
            es.effective_to
        FROM employee_shifts es
        JOIN employees e ON e.employee_id = es.employee_id
        JOIN shifts s ON s.shift_id = es.shift_id
        WHERE es.effective_from <= %s
          AND (es.effective_to IS NULL OR es.effective_to >= %s)
        ORDER BY s.shift_name, e.first_name;
    """, (date_, date_))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows






# ============================================================
# ✅ GET ALL EMPLOYEES FOR A SHIFT (ACTIVE ASSIGNMENT)
# ============================================================

@router.get("/{shift_id}/employees")
def get_shift_employees(shift_id: int):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.department,
            e.designation,
            es.effective_from,
            es.effective_to
        FROM employee_shifts es
        JOIN employees e ON e.employee_id = es.employee_id
        WHERE es.shift_id = %s
          AND es.effective_to IS NULL
        ORDER BY e.first_name;
    """, (shift_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows

# ============================================================
# 3️⃣ CREATE SHIFT
# ============================================================

@router.post("/")
def create_shift(payload: ShiftCreate):
    try:
        return ShiftDB.add_shift(payload.dict())
    except Exception as e:
        raise HTTPException(400, str(e))

# ============================================================
# 4️⃣ GET SINGLE SHIFT  ✅ SAFE NOW
# ============================================================

@router.get("/{shift_id}")
def get_shift(shift_id: int):
    shift = ShiftDB.get_one(shift_id)
    if not shift:
        raise HTTPException(404, "Shift not found")
    return shift

# ============================================================
# 5️⃣ UPDATE SHIFT
# ============================================================

@router.put("/{shift_id}")
def update_shift(shift_id: int, payload: ShiftUpdate):
    if not ShiftDB.get_one(shift_id):
        raise HTTPException(404, "Shift not found")

    return ShiftDB.update_shift(shift_id, payload.dict())

# ============================================================
# 6️⃣ SOFT DELETE SHIFT
# ============================================================

@router.delete("/{shift_id}")
def delete_shift(shift_id: int):
    ok = ShiftDB.delete_shift(shift_id)
    if not ok:
        raise HTTPException(404, "Shift not found")
    return {"message": "Shift archived successfully"}

# ============================================================
# ✅ 7️⃣ ASSIGN SHIFT TO EMPLOYEE (PRODUCTION SAFE)
# ============================================================

@router.post("/assign")
def assign_shift(req: ShiftAssignRequest):

    if not EmployeeDB.get_one(req.employee_id):
        raise HTTPException(404, "Employee not found")

    if not ShiftDB.get_one(req.shift_id):
        raise HTTPException(404, "Shift not found")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        prev_end = req.effective_from - timedelta(days=1)

        cur.execute("""
            UPDATE employee_shifts
            SET effective_to = %s
            WHERE employee_id = %s
              AND effective_to IS NULL;
        """, (prev_end, req.employee_id))

        cur.execute("""
            INSERT INTO employee_shifts (
                employee_id, shift_id, effective_from, effective_to
            )
            VALUES (%s, %s, %s, NULL)
            RETURNING *;
        """, (req.employee_id, req.shift_id, req.effective_from))

        row = cur.fetchone()
        conn.commit()
        return {"message": "Shift assigned successfully", "assignment": row}

    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))

    finally:
        cur.close()
        conn.close()

# ============================================================
# ✅ 8️⃣ UNASSIGN SHIFT (SAFE)
# ============================================================

@router.delete("/unassign/{employee_id}")
def unassign_shift(employee_id: int):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE employee_shifts
        SET effective_to = CURRENT_DATE
        WHERE employee_id = %s AND effective_to IS NULL;
    """, (employee_id,))

    if cur.rowcount == 0:
        cur.close()
        conn.close()
        raise HTTPException(404, "No active shift to remove")

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Shift unassigned successfully"}

# ============================================================
# ✅ 9️⃣ SHIFT HISTORY
# ============================================================

@router.get("/history/{employee_id}")
def shift_history(employee_id: int):
    return EmployeeShiftDB.get_shift_history(employee_id)
