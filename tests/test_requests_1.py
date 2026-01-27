# tests/test_requests_1.py

import time
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from app.database.connection import get_connection

# ================================
# CONFIG
# ================================
BASE_URL = "http://localhost:8000"
PUNCH_URL = f"{BASE_URL}/faces/punch/test"

EMPLOYEE_ID = 36
TEST_DATE = date(2026, 1, 27)

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


# ================================
# TIME HELPERS
# ================================
def ist(h, m=0):
    """
    Create IST datetime and convert to UTC ISO
    """
    return datetime(
        TEST_DATE.year,
        TEST_DATE.month,
        TEST_DATE.day,
        h,
        m,
        tzinfo=IST,
    ).astimezone(UTC).isoformat()


# ================================
# API CALL
# ================================
def punch(event_time):
    res = requests.post(
        PUNCH_URL,
        params={
            "employee_id": EMPLOYEE_ID,
            "event_time": event_time,
        },
        timeout=40,
    )
    try:
        return res.status_code, res.json()
    except Exception:
        return res.status_code, res.text


# ================================
# CLEANUP
# ================================
def cleanup():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM attendance_events WHERE employee_id=%s;", (EMPLOYEE_ID,))
        cur.execute("DELETE FROM attendance WHERE employee_id=%s;", (EMPLOYEE_ID,))
    conn.commit()
    conn.close()
    time.sleep(0.5)


# ================================
# TESTS (ENGINE-ALIGNED)
# ================================

def test_valid_checkin_and_checkout():
    print("\n🟢 Valid check-in (09:05) and checkout")

    punch(ist(9, 5))           # check-in
    status, body = punch(ist(18, 0))  # check-out

    print(status, body)
    cleanup()


def test_checkin_exact_late_grace_boundary():
    print("\n🟢 Check-in exactly at late grace boundary (09:15)")

    status, body = punch(ist(9, 15))
    print(status, body)
    cleanup()


def test_early_checkin_within_grace_allowed():
    print("\n🟢 Early check-in within grace (08:50) allowed")

    status, body = punch(ist(8, 50))
    print(status, body)
    cleanup()


def test_early_overtime_allowed():
    print("\n🟢 Early overtime allowed (08:15)")

    status, body = punch(ist(8, 15))
    print(status, body)
    cleanup()


def test_checkin_too_early_rejected():
    print("\n🔴 Early check-in beyond max (07:45) rejected")

    status, body = punch(ist(7, 45))
    print(status, body)
    cleanup()


def test_late_checkin_rejected():
    print("\n🔴 Late check-in (09:30) rejected")

    status, body = punch(ist(9, 30))
    print(status, body)
    cleanup()


def test_duplicate_punch_ignored():
    print("\n🟢 Duplicate punch ignored")

    t = ist(9, 5)
    punch(t)

    status, body = punch(
        (datetime.fromisoformat(t) + timedelta(seconds=10)).isoformat()
    )

    print(status, body)
    cleanup()


def test_recheckin_same_day_not_allowed():
    print("\n🔴 Re-check-in same day ignored")

    punch(ist(9, 5))
    punch(ist(18, 0))

    status, body = punch(ist(9, 5))
    print(status, body)
    cleanup()


# ================================
# RUNNER
# ================================
if __name__ == "__main__":
    print("\n🚀 Running ATTENDANCE ENGINE–ALIGNED Tests")

    test_valid_checkin_and_checkout()
    test_checkin_exact_late_grace_boundary()
    test_early_checkin_within_grace_allowed()
    test_early_overtime_allowed()
    test_checkin_too_early_rejected()
    test_late_checkin_rejected()
    test_duplicate_punch_ignored()
    test_recheckin_same_day_not_allowed()

    print("\n✅ All engine-aligned tests completed\n")
