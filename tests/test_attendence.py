import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
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
# API CALL
# =====================================================
def call_api(action_time):
    r = requests.post(
        f"{BASE_URL}/attendance/manual",
        data={
            "employee_id": EMPLOYEE_ID,
            "action_time": action_time,
        },
        timeout=10,
    )
    return r.status_code

# =====================================================
# EXPECTATION ENGINE (CORRECT SOURCES)
# =====================================================
def validate(row, scenario, shift, policy):
    errors = []

    # ---- Late arrival (SHIFT-based)
    if "late_arrival_minutes" in scenario:
        grace = shift["late_grace_minutes"]
        expected = max(0, scenario["late_arrival_minutes"] - grace)
        if row["late_minutes"] != expected:
            errors.append(
                f"late_minutes expected {expected}, got {row['late_minutes']}"
            )

    # ---- Early exit (POLICY-based)
    if "early_exit_minutes" in scenario:
        grace = policy["early_exit_grace_minutes"]
        expected = max(0, scenario["early_exit_minutes"] - grace)
        if row["early_exit_minutes"] != expected:
            errors.append(
                f"early_exit_minutes expected {expected}, got {row['early_exit_minutes']}"
            )

    # ---- Break
    if "break_minutes" in scenario:
        if row["break_minutes"] != scenario["break_minutes"]:
            errors.append(
                f"break_minutes expected {scenario['break_minutes']}, got {row['break_minutes']}"
            )

    # ---- Overtime
    if scenario.get("expect_overtime"):
        if row["overtime_minutes"] <= 0:
            errors.append("overtime_minutes expected > 0")

    # ---- Status
    if "status" in scenario:
        if row["status"] != scenario["status"]:
            errors.append(
                f"status expected {scenario['status']}, got {row['status']}"
            )

    return errors

# =====================================================
# SCENARIOS
# =====================================================
SCENARIOS = [
    {
        "title": "ON TIME – FULL DAY",
        "events": ["09:00:00", "13:00:00", "14:00:00", "18:00:00"],
        "status": "present",
    },
    {
        "title": "LATE ARRIVAL (12 MIN)",
        "events": ["09:12:00", "13:00:00", "14:00:00", "18:00:00"],
        "late_arrival_minutes": 12,
        "status": "present",
    },
    {
        "title": "EARLY EXIT (20 MIN)",
        "events": ["09:00:00", "13:00:00", "14:00:00", "17:40:00"],
        "early_exit_minutes": 20,
        "status": "present",
    },
    {
        "title": "LONG BREAK (90 MIN)",
        "events": ["09:00:00", "13:00:00", "14:30:00", "18:00:00"],
        "break_minutes": 90,
        "status": "present",
    },
    {
        "title": "NO BREAK END",
        "events": ["09:00:00", "13:00:00", "18:00:00"],
        "status": "short_hours",
    },
    {
        "title": "OVERTIME (1 HOUR)",
        "events": ["09:00:00", "13:00:00", "14:00:00", "19:00:00"],
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

    print(
        f"📋 Shift → late_grace={shift['late_grace_minutes']} min\n"
        f"📋 Policy → early_exit_grace={policy['early_exit_grace_minutes']} min"
    )

    passed = failed = 0

    for i, s in enumerate(SCENARIOS, 1):
        print("=" * 80)
        print(f"SCENARIO {i}: {s['title']}")

        clear_attendance()

        for t in s["events"]:
            ts = f"{DATE}T{t}"
            code = call_api(ts)
            print(f"EVENT {t} → HTTP {code}")
            time.sleep(0.2)

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

        errors = validate(row, s, shift, policy)

        if errors:
            print("\n❌ FAILED")
            for e in errors:
                print("  -", e)
            failed += 1
        else:
            print("\n✅ PASSED")
            passed += 1

    print("\n" + "=" * 80)
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print("=" * 80)


if __name__ == "__main__":
    run()
