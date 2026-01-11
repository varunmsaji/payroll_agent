import requests
import json

BASE_URL = "http://localhost:8000"
EMPLOYEE_ID = 36
DATE = "2026-01-11"


def call(action_time, label):
    print("\n" + "=" * 60)
    print(label)
    print("TIME:", action_time)

    resp = requests.post(
        f"{BASE_URL}/attendance/manual",
        data={
            "employee_id": EMPLOYEE_ID,
            "action_time": action_time,
        },
    )

    print("STATUS:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)


def expected(title, data):
    print("\nEXPECTED RESULT:", title)
    for k, v in data.items():
        print(f"  {k}: {v}")


print("⚠️ CLEAN DB FIRST:")
print("""
DELETE FROM attendance_events WHERE employee_id = 36;
DELETE FROM attendance WHERE employee_id = 36;
""")
input("Press ENTER once done...")


# =====================================================
# SCENARIO 1: NORMAL OFFICE DAY (EXPECTED: SHORT HOURS)
# =====================================================
call(f"{DATE}T09:00:00", "CHECK-IN")
call(f"{DATE}T13:00:00", "BREAK START")
call(f"{DATE}T13:30:00", "BREAK END")
call(f"{DATE}T18:00:00", "CHECK-OUT")

expected("NORMAL DAY", {
    "worked_hours": "~8.5",
    "required_hours": "~24",
    "late_minutes": 540,      # 09:00 vs 00:00
    "early_exit_minutes": 359,  # 23:59 vs 18:00
    "status": "short_hours"
})


input("\nClean DB and press ENTER for next test...")


# =====================================================
# SCENARIO 2: HALF DAY (12+ HOURS)
# =====================================================
call(f"{DATE}T06:00:00", "CHECK-IN")
call(f"{DATE}T12:00:00", "BREAK START")
call(f"{DATE}T12:30:00", "BREAK END")
call(f"{DATE}T18:30:00", "CHECK-OUT")

expected("HALF DAY", {
    "worked_hours": "~12",
    "status": "half_day"
})


input("\nClean DB and press ENTER for next test...")


# =====================================================
# SCENARIO 3: FULL DAY (18+ HOURS)
# =====================================================
call(f"{DATE}T00:30:00", "CHECK-IN")
call(f"{DATE}T12:00:00", "BREAK START")
call(f"{DATE}T12:30:00", "BREAK END")
call(f"{DATE}T23:00:00", "CHECK-OUT")

expected("FULL DAY", {
    "worked_hours": "~22",
    "status": "present"
})


print("\nFINAL DB CHECK:")
print("""
SELECT
    date,
    check_in,
    check_out,
    net_hours,
    break_minutes,
    late_minutes,
    early_exit_minutes,
    overtime_minutes,
    status
FROM attendance
WHERE employee_id = 36;
""")
