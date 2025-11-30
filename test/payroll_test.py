"""
Simple end-to-end tester for HRMS Payroll Module

Make sure your FastAPI app is running, e.g.:
    uvicorn app.main:app --reload

Then run:
    python test_payroll_module.py
"""

import requests
import json

# =========================
# CONFIG
# =========================
BASE_URL = "http://127.0.0.1:8000"

EMPLOYEE_ID = 35      # ✅ must exist
YEAR = 2025
MONTH = 11

PAYROLL_BASE = f"{BASE_URL}/hrms/payroll"
POLICY_BASE = f"{BASE_URL}/hrms/payroll/policy"   # ✅ FIXED URL


# =========================
# HELPERS
# =========================

def pretty_print(title, resp):
    print("\n" + "=" * 70)
    print(f"🔹 {title}")
    print(f"Status Code: {resp.status_code}")
    try:
        data = resp.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2, default=str))
    except Exception:
        print("Raw Response Text:")
        print(resp.text)
    print("=" * 70 + "\n")


def post_json(url, payload=None):
    if payload is None:
        payload = {}
    return requests.post(url, json=payload)


def get_json(url, params=None):
    if params is None:
        params = {}
    return requests.get(url, params=params)


# =========================
# TEST SCENARIOS
# =========================

def test_policy_exists():
    print("\n========== TEST 0: PAYROLL POLICY CHECK ==========")

    resp = get_json(POLICY_BASE)
    pretty_print("Get Active Payroll Policy", resp)

    if resp.status_code != 200:
        print("❌ No active payroll policy found.")
    else:
        print("✅ Active payroll policy exists.\n")


def test_generate_single():
    print("\n========== TEST 1: GENERATE PAYROLL (SINGLE EMPLOYEE) ==========")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "year": YEAR,
        "month": MONTH,
    }

    resp = post_json(f"{PAYROLL_BASE}/generate", payload)
    pretty_print("Generate Payroll (Single)", resp)


def test_get_single_payroll():
    print("\n========== TEST 2: FETCH GENERATED PAYROLL (SINGLE EMPLOYEE) ==========")

    params = {"year": YEAR, "month": MONTH}
    resp = get_json(f"{PAYROLL_BASE}/{EMPLOYEE_ID}", params=params)
    pretty_print("Get Payroll for Employee", resp)


def test_status_check():
    print("\n========== TEST 3: PAYROLL STATUS CHECK ==========")

    params = {"year": YEAR, "month": MONTH}
    resp = get_json(f"{PAYROLL_BASE}/status/{EMPLOYEE_ID}", params=params)
    pretty_print("Payroll Status for Employee", resp)


def test_bulk_generate():
    print("\n========== TEST 4: BULK PAYROLL GENERATION ==========")

    payload = {"year": YEAR, "month": MONTH}
    resp = post_json(f"{PAYROLL_BASE}/generate-bulk", payload)
    pretty_print("Bulk Generate Payroll", resp)


def test_regenerate():
    print("\n========== TEST 5: REGENERATE PAYROLL (ADMIN OVERRIDE) ==========")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "year": YEAR,
        "month": MONTH,
    }

    resp = post_json(f"{PAYROLL_BASE}/regenerate", payload)
    pretty_print("Regenerate Payroll for Employee", resp)


def test_month_list():
    print("\n========== TEST 6: LIST ALL PAYROLL ENTRIES FOR MONTH ==========")

    params = {"year": YEAR, "month": MONTH}
    resp = get_json(f"{PAYROLL_BASE}/month/list", params=params)
    pretty_print("Month-wise Payroll List", resp)


def test_invalid_employee():
    print("\n========== TEST 7: INVALID EMPLOYEE ID HANDLING ==========")

    payload = {
        "employee_id": 999999,   # non-existent
        "year": YEAR,
        "month": MONTH,
    }

    resp = post_json(f"{PAYROLL_BASE}/generate", payload)
    pretty_print("Generate Payroll for Invalid Employee", resp)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("🚀 Starting Payroll Module Tests against:", BASE_URL)
    print(f"Using employee_id={EMPLOYEE_ID}, year={YEAR}, month={MONTH}")

    test_policy_exists()
    test_generate_single()
    test_get_single_payroll()
    test_status_check()
    test_bulk_generate()
    test_regenerate()
    test_month_list()
    test_invalid_employee()

    print("\n✅ Test script finished. Review the logs above for any errors or odd data.")
