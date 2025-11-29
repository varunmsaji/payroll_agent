# Future Improvements & Fixes

## 🟡 1️⃣ DATE TYPE SAFETY (LOGIC UPGRADE — NO DB CHANGE)
**❌ CURRENT RISK**
You accept string dates directly from frontend.

**✅ FUTURE FIX**
In `/hrms/leaves/apply`:
```python
from datetime import date

start_date = date.fromisoformat(req["start_date"])
end_date = date.fromisoformat(req["end_date"])
```
Also add:
```python
if end_date < start_date:
    raise HTTPException(400, "end_date cannot be before start_date")
```
- ✅ Prevents timezone bugs
- ✅ Prevents inverted date ranges

## 🟡 2️⃣ DOUBLE LEAVE APPLY RACE CONDITION (DATA SAFETY)
**❌ CURRENT RISK**
Two parallel API requests can over-apply before approval.

**✅ FUTURE FIX**
Before applying leave:
```python
balance = LeaveBalanceDB.get_single_balance(employee_id, leave_type_id, year)

if float(balance["remaining"]) < total_days:
    raise HTTPException(400, "Insufficient leave balance")
```
- ✅ Prevents overbooking
- ✅ Prevents finance miscalculations

## 🟡 3️⃣ WORKFLOW FAILURE PROTECTION
**❌ CURRENT RISK**
If workflow start fails → leave stays pending forever.

**✅ FUTURE FIX**
Wrap this safely:
```python
try:
    workflow_db.start_workflow(...)
except:
    LeaveRequestDB.update_leave_status_only(leave_id, "rejected")
    raise HTTPException(500, "Workflow failed")
```
- ✅ Prevents dead stuck leave rows

## 🟡 4️⃣ REQUEST PAGINATION (PERFORMANCE)
**❌ CURRENT RISK**
This will crash UI as volume grows:
`@router.get("/requests")`

**✅ FUTURE FIX**
Add:
```python
def get_all_requests(page=1, limit=50):
```
- ✅ Prevents memory overload
- ✅ Frontend friendly

## 🟡 5️⃣ SALARY ENDPOINT SECURITY (RBAC)
**❌ CURRENT RISK**
Any user can query:
`/hrms/leaves/salary/{id}/{year}/{month}`

**✅ FUTURE FIX**
Block unless:
- HR
- Admin
- Finance

- ✅ Prevents major data leaks

## 🟡 6️⃣ DB LEVEL STATUS HARDENING (OPTIONAL MIGRATION)
**❌ CURRENT:**
`status VARCHAR(20)`

**✅ FUTURE:**
`status VARCHAR(20) CHECK (status IN ('pending','approved','rejected'))`
- ✅ Prevents corrupted workflow states

## 🟡 7️⃣ AUTO LEAVE EXPIRY (NEXT VERSION FEATURE)
Auto-carry forward expiry engine (optional):
- Cron job at year-end
- Uses carry_forward flag from leave types

---

# Next Production-Critical Modules

## 🔥 1️⃣ Attendance Locking System
- Prevent duplicate punches
- Time window validation
- Device/IP fingerprint

## 🔥 2️⃣ Payroll Approval Workflow
- Auto compute → HR approve → Finance release

## 🔥 3️⃣ RBAC (Access Control)
- Admin / HR / Manager / Employee
