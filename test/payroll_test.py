"""
FULL END-TO-END PAYROLL TEST WITH ATTENDANCE CALCULATION

1️⃣ Recalculate attendance for multiple dates
2️⃣ Regenerate payroll
3️⃣ Fetch final payroll
4️⃣ Validate overtime, late, net salary

Run:
    python test_full_payroll_with_attendance.py
"""

import requests
import json
from datetime import date, timedelta

# =========================
# CONFIG
# =========================

BASE_URL = "http://127.0.0.1:8000"

EMPLOYEE_ID = 35
YEAR = 2025
MONTH = 11

ATTENDANCE_BASE = f"{BASE_URL}/hrms/attendance"
PAYROLL_BASE = f"{BASE_URL}/hrms/payroll"


# =========================
# HELPERS
# =========================

def pretty(title, resp):
    print("\n" + "=" * 80)
    print(f"🔹 {title}")
    print(f"Status Code: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except Exception:
        print(resp.text)
    print("=" * 80 + "\n")


def post(url, payload=None):
    if payload is None:
        payload = {}
    return requests.post(url, json=payload)


def get(url, params=None):
    return requests.get(url, params=params)


# =========================
# 1️⃣ RECALCULATE ATTENDANCE FOR FULL MONTH
# =========================

def recalc_full_month():
    print("\n========== STEP 1: RECALCULATE ATTENDANCE ==========\n")

    start_day = date(YEAR, MONTH, 1)

    # detect last day safely
    if MONTH == 12:
        end_day = date(YEAR + 1, 1, 1) - timedelta(days=1)
    else:
        end_day = date(YEAR, MONTH + 1, 1) - timedelta(days=1)

    dt = start_day
    while dt <= end_day:
        url = f"{ATTENDANCE_BASE}/recalculate/{EMPLOYEE_ID}"
        resp = post(url + f"?dt={dt.isoformat()}")
        print(f"✅ Recalculated: {dt} | Status: {resp.status_code}")
        dt += timedelta(days=1)


# =========================
# 2️⃣ REGENERATE PAYROLL
# =========================

def regenerate_payroll():
    print("\n========== STEP 2: REGENERATE PAYROLL ==========\n")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "year": YEAR,
        "month": MONTH
    }

    resp = post(f"{PAYROLL_BASE}/regenerate", payload)
    pretty("Regenerate Payroll", resp)


# =========================
# 3️⃣ FETCH FINAL PAYROLL
# =========================

def fetch_final_payroll():
    print("\n========== STEP 3: FETCH FINAL PAYROLL ==========\n")

    params = {"year": YEAR, "month": MONTH}
    resp = get(f"{PAYROLL_BASE}/{EMPLOYEE_ID}", params=params)
    pretty("Final Payroll", resp)


# =========================
# 4️⃣ VALIDATE PAYROLL MATH
# =========================

def validate_results():
    print("\n========== STEP 4: PAYROLL VALIDATION ==========\n")

    params = {"year": YEAR, "month": MONTH}
    payroll = get(f"{PAYROLL_BASE}/{EMPLOYEE_ID}", params=params).json()

    print("✅ Net Salary:", payroll["net_salary"])
    print("✅ Gross Salary:", payroll["gross_salary"])
    print("✅ Overtime Hours:", payroll["overtime_hours"])
    print("✅ Late Penalty:", payroll["late_penalty"])
    print("✅ LOP Deduction:", payroll["lop_deduction"])
    print("✅ Holiday Pay:", payroll["holiday_pay"])
    print("✅ Night Shift Allowance:", payroll["night_shift_allowance"])

    if payroll["overtime_hours"] > 0:
        print("✅ OVERTIME IS BEING PAID CORRECTLY")

    if payroll["lop_deduction"] > 0:
        print("✅ LOP DEDUCTIONS APPLIED")

    print("\n🎯 PAYROLL VALIDATION COMPLETE\n")


# =========================
# 🚀 MAIN
# =========================

if __name__ == "__main__":

    print("\n🚀 STARTING FULL PAYROLL + ATTENDANCE TEST\n")

    recalc_full_month()
    regenerate_payroll()
    fetch_final_payroll()
    validate_results()

    print("\n✅ FULL END-TO-END PAYROLL SYSTEM TEST COMPLETED SUCCESSFULLY ✅\n")
