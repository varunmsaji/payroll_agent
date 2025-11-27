import requests
import sys

BASE_URL = "http://127.0.0.1:8000"


def fail(msg):
    print(f"\n❌ TEST FAILED: {msg}")
    sys.exit(1)


def ok(msg):
    print(f"✅ {msg}")


# ============================================
# ✅ TEST: CHECK IF HR ROLE EXISTS
# ============================================
def test_hr_role_exists():
    print("\n--- Checking if HR Role is Assigned ---")

    r = requests.get(f"{BASE_URL}/hrms/employees")

    if r.status_code != 200:
        fail(f"Failed to fetch employees → {r.text}")

    employees = r.json()

    if not employees:
        fail("No employees found in system")

    hr_users = []

    for emp in employees:
        designation = (emp.get("designation") or "").lower()
        if "hr" in designation:
            hr_users.append(emp)

    if not hr_users:
        fail(
            "No HR user found ❌\n"
            "👉 Assign HR designation to at least one employee.\n"
            "Example SQL:\n"
            "UPDATE employees SET designation='HR' WHERE employee_id = 2;"
        )

    ok(f"HR role is correctly assigned ✅ ({len(hr_users)} HR found)")

    print("\n👤 HR USERS FOUND:")
    for hr in hr_users:
        print(
            f" - ID: {hr['employee_id']}, "
            f"Name: {hr.get('first_name')} {hr.get('last_name')}, "
            f"Designation: {hr.get('designation')}"
        )


# ============================================
# ✅ MAIN RUNNER
# ============================================
if __name__ == "__main__":
    print("\n==============================")
    print("🚀 STARTING HR ROLE TEST")
    print("==============================")

    test_hr_role_exists()

    print("\n==============================")
    print("✅✅✅ HR ROLE TEST PASSED ✅✅✅")
    print("==============================")
