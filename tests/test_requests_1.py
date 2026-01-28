import time
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from app.database.connection import get_connection

# ======================================================
# CONFIG
# ======================================================
BASE_URL = "http://localhost:8000"
PUNCH_URL = f"{BASE_URL}/faces/punch/test"

EMPLOYEE_ID = 36
TEST_DATE = date(2026, 1, 27)

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


# ======================================================
# TIME HELPERS
# ======================================================
def ist(h, m=0):
    return datetime(
        TEST_DATE.year,
        TEST_DATE.month,
        TEST_DATE.day,
        h,
        m,
        tzinfo=IST,
    ).astimezone(UTC).isoformat()


# ======================================================
# API CALL
# ======================================================
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


# ======================================================
# DB HELPERS
# ======================================================
def print_final_state():
    conn = get_connection()
    with conn.cursor() as cur:
        print("\n📊 ATTENDANCE TABLE")
        cur.execute(
            """
            SELECT
                date,
                check_in,
                check_out,
                total_hours,
                net_hours,
                break_minutes,
                late_minutes,
                early_exit_minutes,
                overtime_minutes,
                status
            FROM attendance
            WHERE employee_id=%s
            ORDER BY date DESC
            LIMIT 1;
            """,
            (EMPLOYEE_ID,),
        )
        row = cur.fetchone()
        for k, v in zip(
            [
                "date",
                "check_in",
                "check_out",
                "total_hours",
                "net_hours",
                "break_minutes",
                "late_minutes",
                "early_exit_minutes",
                "overtime_minutes",
                "status",
            ],
            row,
        ):
            print(f"{k:20}: {v}")

        print("\n📜 EVENTS")
        cur.execute(
            """
            SELECT event_type, event_time, meta
            FROM attendance_events
            WHERE employee_id=%s
            ORDER BY event_time;
            """,
            (EMPLOYEE_ID,),
        )
        for e in cur.fetchall():
            print(e)

    conn.close()


def cleanup():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM attendance_events WHERE employee_id=%s;", (EMPLOYEE_ID,))
        cur.execute("DELETE FROM attendance WHERE employee_id=%s;", (EMPLOYEE_ID,))
    conn.commit()
    conn.close()
    time.sleep(0.5)


# ======================================================
# FULL DAY SCENARIOS
# ======================================================

def scenario_perfect_day():
    print("\n🟢 PERFECT DAY (on time + full break)")
    punch(ist(9, 0))
    punch(ist(11, 0))
    punch(ist(12, 0))
    punch(ist(18, 0))
    print_final_state()
    cleanup()


def scenario_late_within_grace():
    print("\n🟡 LATE WITHIN GRACE (09:10)")
    punch(ist(9, 10))
    punch(ist(11, 0))
    punch(ist(12, 0))
    punch(ist(18, 0))
    print_final_state()
    cleanup()


def scenario_late_beyond_grace():
    print("\n🔴 LATE BEYOND GRACE (09:30)")
    status, body = punch(ist(9, 30))
    print(status, body)
    cleanup()


def scenario_early_within_grace():
    print("\n🟢 EARLY WITHIN GRACE (08:50)")
    punch(ist(8, 50))
    punch(ist(11, 0))
    punch(ist(12, 0))
    punch(ist(18, 0))
    print_final_state()
    cleanup()


def scenario_early_overtime():
    print("\n🟢 EARLY OVERTIME (08:15)")
    punch(ist(8, 15))
    punch(ist(11, 0))
    punch(ist(12, 0))
    punch(ist(18, 0))
    print_final_state()
    cleanup()


def scenario_early_beyond_max():
    print("\n🔴 EARLY BEYOND MAX (07:45)")
    status, body = punch(ist(7, 45))
    print(status, body)
    cleanup()


def scenario_no_break_violation():
    print("\n🔴 NO BREAK → SHORT HOURS")
    punch(ist(9, 0))
    punch(ist(18, 0))
    print_final_state()
    cleanup()


def scenario_overtime_day():
    print("\n🟢 OVERTIME DAY")
    punch(ist(9, 0))
    punch(ist(11, 0))
    punch(ist(12, 0))
    punch(ist(19, 30))
    print_final_state()
    cleanup()


# ======================================================
# RUNNER
# ======================================================
if __name__ == "__main__":
    print("\n🚀 RUNNING FULL PRODUCTION SCENARIOS")

    scenario_perfect_day()
    scenario_late_within_grace()
    scenario_late_beyond_grace()
    scenario_early_within_grace()
    scenario_early_overtime()
    scenario_early_beyond_max()
    scenario_no_break_violation()
    scenario_overtime_day()

    print("\n✅ ALL PRODUCTION SCENARIOS COMPLETED\n")
