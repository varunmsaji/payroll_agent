import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import time
import os

# =====================================================
# CONFIG
# =====================================================
# BASE_URL = "http://localhost:8000"
BASE_URL ="https://varunmsaji01-hrms-backend-latest.hf.space"


EMPLOYEE_ID = 36
DATE = "2026-01-11"
IMAGE_PATH = "varun_test.jpg"

DATABASE_URL = "postgresql://postgres:t3dPZJwoCApEGgBU@db.fmhhqmmntpnxxqvnffej.supabase.co:5432/postgres"
USE_SSL = "supabase.co" in DATABASE_URL

if not os.path.exists(IMAGE_PATH):
    raise RuntimeError("❌ Face image not found")

# =====================================================
# DB HELPERS
# =====================================================
def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require" if USE_SSL else "disable",
    )


def clear_attendance():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM attendance_events WHERE employee_id = %s;
                DELETE FROM attendance WHERE employee_id = %s;
                """,
                (EMPLOYEE_ID, EMPLOYEE_ID),
            )


def fetch_attendance():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM attendance
                WHERE employee_id = %s
                ORDER BY date DESC
                LIMIT 1;
                """,
                (EMPLOYEE_ID,),
            )
            return cur.fetchone()


# =====================================================
# FACE PUNCH CALL
# =====================================================
def face_punch(fake_time: str):
    ts = datetime.fromisoformat(f"{DATE}T{fake_time}").replace(
        tzinfo=timezone.utc
    )

    files = {
        "file": ("face.jpg", open(IMAGE_PATH, "rb"), "image/jpeg")
    }

    params = {
        "event_time": ts.isoformat()
    }

    r = requests.post(
        f"{BASE_URL}/faces/punch",
        files=files,
        params=params,
        timeout=60,
    )

    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


# =====================================================
# SCENARIOS
# =====================================================
SCENARIOS = [
    {
        "title": "ON TIME – FULL DAY",
        "events": ["09:00", "13:00", "14:00", "18:00"],
    },
    {
        "title": "LATE ARRIVAL (12 MIN)",
        "events": ["09:12", "13:00", "14:00", "18:00"],
    },
    {
        "title": "EARLY EXIT (20 MIN)",
        "events": ["09:00", "13:00", "14:00", "17:40"],
    },
    {
        "title": "OVERTIME (1 HOUR)",
        "events": ["09:00", "13:00", "14:00", "19:00"],
    },
]

# =====================================================
# RESULT PRINTER
# =====================================================
def print_result(row):
    print("\n📊 FINAL ATTENDANCE")
    print("-" * 60)

    for k in [
        "check_in",
        "check_out",
        "net_hours",
        "break_minutes",
        "late_minutes",
        "early_exit_minutes",
        "overtime_minutes",
        "status",
    ]:
        print(f"{k:22}: {row.get(k)}")

    print("-" * 60)


# =====================================================
# RUNNER
# =====================================================
def run():
    print("\n🚀 FACE ATTENDANCE TESTS\n")

    for i, s in enumerate(SCENARIOS, 1):
        print("=" * 70)
        print(f"TEST {i}: {s['title']}")
        print("=" * 70)

        clear_attendance()

        for t in s["events"]:
            code, res = face_punch(t)
            action = res.get("action") if isinstance(res, dict) else None
            print(f"FACE {t} → HTTP {code} | action={action}")
            time.sleep(1.2)

        row = fetch_attendance()

        if row:
            print_result(row)
        else:
            print("❌ No attendance record created")

    print("\n✅ ALL FACE TESTS COMPLETED\n")


if __name__ == "__main__":
    run()
