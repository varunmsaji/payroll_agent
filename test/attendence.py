"""
Simple end-to-end tester for HRMS Attendance Module

Make sure your FastAPI app is running, e.g.:
    uvicorn app.main:app --reload

Then run:
    python test_attendance_module.py
"""

import requests
from datetime import date
import json
import time
from typing import Optional, Dict

# =========================
# CONFIG
# =========================
BASE_URL = "http://localhost:8000"   # change if needed
EMPLOYEE_ID = 35
                    # use an existing employee_id in your DB

ATTENDANCE_BASE = f"{BASE_URL}/hrms/attendance"


# =========================
# HELPER FUNCTIONS
# =========================
def pretty_print(title: str, resp: requests.Response):
    print("\n" + "=" * 60)
    print(f"🔹 {title}")
    print(f"Status Code: {resp.status_code}")
    try:
        data = resp.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2, default=str))
    except Exception:
        print("Raw Response Text:")
        print(resp.text)
    print("=" * 60 + "\n")


def post_json(url: str, payload: Optional[Dict] = None, params: Optional[Dict] = None) -> requests.Response:
    if payload is None:
        payload = {}
    return requests.post(url, json=payload, params=params or {})


def get_json(url: str, params: Optional[Dict] = None) -> requests.Response:
    return requests.get(url, params=params or {})


# =========================
# TEST SCENARIOS
# =========================

def test_basic_check_in_out():
    print("\n========== TEST 1: BASIC CHECK-IN / CHECK-OUT ==========")

    # 1) Check-in
    resp_in = post_json(
        f"{ATTENDANCE_BASE}/check-in",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "basic_check_in_out"},
        },
    )
    pretty_print("Check-in", resp_in)

    time.sleep(1)

    # 2) Check-out
    resp_out = post_json(
        f"{ATTENDANCE_BASE}/check-out",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "basic_check_in_out"},
        },
    )
    pretty_print("Check-out", resp_out)

    # 3) Fetch attendance for today
    today = date.today().isoformat()
    resp_get = get_json(
        f"{ATTENDANCE_BASE}/employee/{EMPLOYEE_ID}",
        params={"start_date": today, "end_date": today},
    )
    pretty_print("Get Attendance for Today (after basic check-in/out)", resp_get)


def test_break_flow():
    print("\n========== TEST 2: CHECK-IN → BREAK → BREAK END → CHECK-OUT ==========")

    today = date.today().isoformat()

    # 1) Check-in
    resp_in = post_json(
        f"{ATTENDANCE_BASE}/check-in",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "break_flow"},
        },
    )
    pretty_print("Check-in (break flow)", resp_in)

    time.sleep(1)

    # 2) Break start
    resp_break_start = post_json(
        f"{ATTENDANCE_BASE}/break/start",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "break_flow"},
        },
    )
    pretty_print("Break Start", resp_break_start)

    time.sleep(1)

    # 3) Break end
    resp_break_end = post_json(
        f"{ATTENDANCE_BASE}/break/end",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "break_flow"},
        },
    )
    pretty_print("Break End", resp_break_end)

    time.sleep(1)

    # 4) Check-out
    resp_out = post_json(
        f"{ATTENDANCE_BASE}/check-out",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "break_flow"},
        },
    )
    pretty_print("Check-out (break flow)", resp_out)

    # 5) Fetch attendance row
    resp_get = get_json(
        f"{ATTENDANCE_BASE}/employee/{EMPLOYEE_ID}",
        params={"start_date": today, "end_date": today},
    )
    pretty_print("Get Attendance for Today (after break flow)", resp_get)


def test_recalculate_and_lock():
    print("\n========== TEST 3: RECALCULATE & PAYROLL LOCK ==========")

    today = date.today().isoformat()

    # 1) Recalculate today ✅ FIXED: params now supported
    resp_recalc = post_json(
        f"{ATTENDANCE_BASE}/recalculate/{EMPLOYEE_ID}",
        params={"dt": today},
    )
    pretty_print("Recalculate Attendance for Today", resp_recalc)

    # 2) Lock attendance for today
    resp_lock = post_json(
        f"{ATTENDANCE_BASE}/lock/{EMPLOYEE_ID}",
        params={"dt": today},
    )
    pretty_print("Lock Attendance for Today", resp_lock)

    # 3) Try recalculating again after lock (should fail)
    resp_recalc_locked = post_json(
        f"{ATTENDANCE_BASE}/recalculate/{EMPLOYEE_ID}",
        params={"dt": today},
    )
    pretty_print("Recalculate After Lock (should fail)", resp_recalc_locked)


def test_invalid_flows():
    print("\n========== TEST 4: INVALID FLOWS / ERROR HANDLING ==========")

    # 1) Try check-out without check-in (assumes no active session)
    resp_checkout_no_checkin = post_json(
        f"{ATTENDANCE_BASE}/check-out",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "invalid_no_checkin"},
        },
    )
    pretty_print("Check-out without active check-in (should error)", resp_checkout_no_checkin)

    # 2) Try break-end without break-start
    resp_break_end_no_start = post_json(
        f"{ATTENDANCE_BASE}/break/end",
        {
            "employee_id": EMPLOYEE_ID,
            "source": "test_script",
            "meta": {"scenario": "invalid_no_break_start"},
        },
    )
    pretty_print("Break End without Break Start (should error)", resp_break_end_no_start)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("🚀 Starting Attendance Module Tests against:", BASE_URL)
    print(f"Using employee_id={EMPLOYEE_ID}")

    test_basic_check_in_out()
    test_break_flow()
    test_recalculate_and_lock()
    test_invalid_flows()

    print("\n✅ Test script finished. Review the logs above for any errors or odd data.")