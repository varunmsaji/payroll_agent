import os
import time
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

# ----------------------------------
# DB CLEANUP IMPORT (YOUR CODE)
# ----------------------------------
from app.database.connection import get_connection

# ================================
# CONFIG
# ================================
BASE_URL = "http://localhost:8000"
PUNCH_URL = f"{BASE_URL}/faces/punch"

EMPLOYEE_ID = 36
TEST_DATE = date(2026, 1, 27)

IMAGE_PATH = 'tests/varun_tele.jpg' # 🔥 FACE IMAGE

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

if not os.path.exists(IMAGE_PATH):
    raise RuntimeError(f"Face image not found: {IMAGE_PATH}")

# ================================
# TIME HELPERS
# ================================
def ist(h, m=0):
    """
    Create IST datetime for test date and convert to UTC ISO string
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
# FACE PUNCH API CALL
# ================================
def punch(event_time):
    with open(IMAGE_PATH, "rb") as img:
        files = {
            "file": ("test.jpg", img, "image/jpeg"),
        }

        params = {
            "event_time": event_time,
        }

        res = requests.post(
            PUNCH_URL,
            files=files,
            params=params,
            timeout=30,  # ML + DB
        )

    try:
        return res.status_code, res.json()
    except Exception:
        return res.status_code, res.text


# ================================
# DB CLEANUP (REAL)
# ================================
def cleanup_employee_attendance(employee_id: int):
    """
    Deletes attendance + attendance_events for given employee.
    Safe for test usage.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM attendance_events WHERE employee_id = %s;",
                (employee_id,),
            )
            cur.execute(
                "DELETE FROM attendance WHERE employee_id = %s;",
                (employee_id,),
            )

        conn.commit()
        print(f"🧹 Cleanup done for employee_id={employee_id}")

    except Exception as e:
        print("❌ Cleanup failed:", e)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def cleanup():
    cleanup_employee_attendance(EMPLOYEE_ID)
    time.sleep(0.3)


# ================================
# TEST SCENARIOS
# ================================
def test_perfect_day():
    print("\n🟢 TEST: Perfect day with break")

    punch(ist(9, 0))
    punch(ist(11, 0))
    punch(ist(12, 0))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_late_within_grace():
    print("\n🟢 TEST: Late within grace (09:10)")

    punch(ist(9, 10))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_late_beyond_grace():
    print("\n🟠 TEST: Late beyond grace (09:30)")

    punch(ist(9, 30))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_very_late_rejected():
    print("\n🔴 TEST: Very late check-in rejected (10:00)")

    status, body = punch(ist(10, 0))
    print("Response:", status, body)

    cleanup()


def test_early_checkout():
    print("\n🟠 TEST: Early checkout (16:30)")

    punch(ist(9, 0))
    status, body = punch(ist(16, 30))

    print("Final punch:", status, body)
    cleanup()


def test_overtime():
    print("\n🟢 TEST: Overtime (19:30)")

    punch(ist(9, 0))
    status, body = punch(ist(19, 30))

    print("Final punch:", status, body)
    cleanup()


def test_early_checkin_within_grace():
    print("\n🟢 TEST: Early check-in within grace (08:50)")

    punch(ist(8, 50))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_early_overtime():
    print("\n🟠 TEST: Early overtime (08:00)")

    punch(ist(8, 0))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_break_violation():
    print("\n🟠 TEST: Break violation (no break taken)")

    punch(ist(9, 0))
    status, body = punch(ist(18, 0))

    print("Final punch:", status, body)
    cleanup()


def test_duplicate_punch():
    print("\n🟢 TEST: Duplicate punch")

    t = ist(9, 0)
    punch(t)

    status, body = punch(
        (datetime.fromisoformat(t) + timedelta(seconds=10)).isoformat()
    )

    print("Duplicate response:", status, body)
    cleanup()


# ================================
# MAIN RUNNER
# ================================
if __name__ == "__main__":
    print("\n🚀 Starting FACE Attendance API End-to-End Tests")

    test_perfect_day()
    test_late_within_grace()
    test_late_beyond_grace()
    test_very_late_rejected()
    test_early_checkout()
    test_overtime()
    test_early_checkin_within_grace()
    test_early_overtime()
    test_break_violation()
    test_duplicate_punch()

    print("\n✅ All FACE attendance tests executed successfully\n")
