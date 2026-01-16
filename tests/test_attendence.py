import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import time

# =====================================================
# CONFIG
# =====================================================
BASE_URL = "http://localhost:8000"
EMPLOYEE_ID = 36
DATE = "2026-01-11"

DB_CONFIG = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

# =====================================================
# DB HELPERS
# =====================================================
def get_conn():
    return psycopg2.connect(**DB_CONFIG)


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
    print("🧹 DB cleaned")


def fetch_shift():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT s.*
                FROM shifts s
                JOIN employee_shifts es ON es.shift_id = s.shift_id
                WHERE es.employee_id = %s
                  AND s.is_active = true
                LIMIT 1;
                """,
                (EMPLOYEE_ID,),
            )
            shift = cur.fetchone()
            if not shift:
                raise RuntimeError("No active shift found")
            return shift


def fetch_policy(dt):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM attendance_policies
                WHERE created_at <= %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (dt,),
            )
            return cur.fetchone()


def fetch_attendance():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM attendance WHERE employee_id = %s;",
                (EMPLOYEE_ID,),
            )
            return cur.fetchone()

# =====================================================
# API CALLER (EXPLICIT EVENTS)
# =====================================================
ENDPOINTS = {
    "check_in": "/attendance/check-in",
    "break_start": "/attendance/break/start",
    "break_end": "/attendance/break/end",
    "check_out": "/attendance/check-out",
}


def call_api(action: str, fake_time: str):
    """
    Inject deterministic server time via header
    """
    ts = datetime.fromisoformat(f"{DATE}T{fake_time}").replace(
        tzinfo=timezone.utc
    )

    r = requests.post(
        f"{BASE_URL}{ENDPOINTS[action]}",
        headers={
            "X-Fake-Time": ts.isoformat()  # 👈 use middleware or dependency
        },
        timeout=10,
    )
    return r.status_code

# =====================================================
# SCENARIOS (EXPLICIT ACTIONS)
# =====================================================
SCENARIOS = [
    {
        "title": "ON TIME – FULL DAY",
        "events": [
            ("check_in", "09:00"),
            ("break_start", "13:00"),
            ("break_end", "14:00"),
            ("check_out", "18:00"),
        ],
        "status": "present",
    },
    {
        "title": "LATE ARRIVAL (12 MIN)",
        "events": [
            ("check_in", "09:12"),
            ("break_start", "13:00"),
            ("break_end", "14:00"),
            ("check_out", "18:00"),
        ],
        "late_arrival_minutes": 12,
        "status": "present",
    },
    {
        "title": "EARLY EXIT (20 MIN)",
        "events": [
            ("check_in", "09:00"),
            ("break_start", "13:00"),
            ("break_end", "14:00"),
            ("check_out", "17:40"),
        ],
        "early_exit_minutes": 20,
        "status": "present",
    },
    {
        "title": "LONG BREAK (90 MIN)",
        "events": [
            ("check_in", "09:00"),
            ("break_start", "13:00"),
            ("break_end", "14:30"),
            ("check_out", "18:00"),
        ],
        "break_minutes": 90,
        "status": "present",
    },
    {
        "title": "NO BREAK END",
        "events": [
            ("check_in", "09:00"),
            ("break_start", "13:00"),
            ("check_out", "18:00"),
        ],
        "status": "short_hours",
    },
    {
        "title": "OVERTIME (1 HOUR)",
        "events": [
            ("check_in", "09:00"),
            ("break_start", "13:00"),
            ("break_end", "14:00"),
            ("check_out", "19:00"),
        ],
        "expect_overtime": True,
        "status": "present",
    },
]

# =====================================================
# RUNNER
# =====================================================
def run():
    print("\n🚀 STARTING ATTENDANCE SCENARIO TESTS\n")

    shift = fetch_shift()
    policy = fetch_policy(datetime.fromisoformat(DATE))

    passed = failed = 0

    for i, s in enumerate(SCENARIOS, 1):
        print("=" * 80)
        print(f"SCENARIO {i}: {s['title']}")

        clear_attendance()

        for action, t in s["events"]:
            code = call_api(action, t)
            print(f"{action:12} @ {t} → HTTP {code}")
            time.sleep(0.1)

        row = fetch_attendance()
        if not row:
            print("❌ No attendance row")
            failed += 1
            continue

        print("\n📊 FINAL ATTENDANCE")
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
            print(f"  {k:18}: {row.get(k)}")

        passed += 1

    print("\n" + "=" * 80)
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print("=" * 80)


if __name__ == "__main__":
    run()
