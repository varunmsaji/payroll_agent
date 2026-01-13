import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"
EMPLOYEE_ID = 36
TEST_DATE = "2026-01-11"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def cleanup_db():
    print("\n🧹 Cleaning DB...")
    requests.post(
        f"{BASE_URL}/attendance/debug/cleanup",
        json={"employee_id": EMPLOYEE_ID},
    )


def call(action_time: str, label: str):
    print(f"\n➡️ {label} @ {action_time}")
    resp = requests.post(
        f"{BASE_URL}/attendance/manual",
        data={
            "employee_id": EMPLOYEE_ID,
            "action_time": action_time,
        },
    )
    print("STATUS:", resp.status_code)

    if resp.status_code != 200:
        print("❌ API ERROR:", resp.text)
        return False

    return True


def fetch_attendance():
    resp = requests.get(
        f"{BASE_URL}/attendance/debug/{EMPLOYEE_ID}/{TEST_DATE}"
    )
    return resp.json()


def assert_result(actual, expected):
    errors = []

    for key, exp_val in expected.items():
        if actual.get(key) != exp_val:
            errors.append(f"{key}: expected {exp_val}, got {actual.get(key)}")

    if errors:
        print("❌ FAIL")
        for e in errors:
            print("   -", e)
    else:
        print("✅ PASS")


# ------------------------------------------------------------
# Scenario Runner
# ------------------------------------------------------------
def run_scenario(name, actions, expected):
    print("\n" + "=" * 80)
    print(f"🧪 SCENARIO: {name}")

    cleanup_db()

    for action in actions:
        ok = call(action["time"], action["label"])
        if not ok:
            print("❌ Scenario aborted due to API error")
            return

    attendance = fetch_attendance()

    print("\n📊 FINAL ATTENDANCE:")
    print(json.dumps(attendance, indent=2))

    assert_result(attendance, expected)


# ------------------------------------------------------------
# TEST CASES
# ------------------------------------------------------------

run_scenario(
    "NORMAL BREAK (INSIDE WINDOW)",
    [
        {"label": "CHECK-IN", "time": "2026-01-11T09:00:00"},
        {"label": "BREAK START", "time": "2026-01-11T11:00:00"},
        {"label": "BREAK END", "time": "2026-01-11T12:00:00"},
        {"label": "CHECK-OUT", "time": "2026-01-11T18:00:00"},
    ],
    expected={
        "status": "present",
        "break_minutes": 60,
    },
)

run_scenario(
    "BREAK END WITHIN GRACE",
    [
        {"label": "CHECK-IN", "time": "2026-01-11T09:00:00"},
        {"label": "BREAK START", "time": "2026-01-11T11:00:00"},
        {"label": "BREAK END (GRACE)", "time": "2026-01-11T12:10:00"},
        {"label": "CHECK-OUT", "time": "2026-01-11T18:00:00"},
    ],
    expected={
        "status": "present",
        "break_minutes": 70,
    },
)

run_scenario(
    "BREAK END AFTER GRACE (VIOLATION)",
    [
        {"label": "CHECK-IN", "time": "2026-01-11T09:00:00"},
        {"label": "BREAK START", "time": "2026-01-11T11:00:00"},
        {"label": "BREAK END (LATE)", "time": "2026-01-11T12:25:00"},
        {"label": "CHECK-OUT", "time": "2026-01-11T18:00:00"},
    ],
    expected={
        "status": "short_hours",
    },
)

run_scenario(
    "BREAK START BEFORE WINDOW",
    [
        {"label": "CHECK-IN", "time": "2026-01-11T09:00:00"},
        {"label": "BREAK START (INVALID)", "time": "2026-01-11T10:30:00"},
        {"label": "BREAK END", "time": "2026-01-11T11:15:00"},
        {"label": "CHECK-OUT", "time": "2026-01-11T18:00:00"},
    ],
    expected={
        "status": "short_hours",
    },
)

run_scenario(
    "NO BREAK TAKEN (MANDATORY BREAK)",
    [
        {"label": "CHECK-IN", "time": "2026-01-11T09:00:00"},
        {"label": "CHECK-OUT", "time": "2026-01-11T18:00:00"},
    ],
    expected={
        "status": "short_hours",
    },
)

print("\n🎉 ALL SCENARIOS EXECUTED")
