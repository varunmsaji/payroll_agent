import requests
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

# =========================
# ✅ YOUR REAL CONFIG
# =========================
EMPLOYEE_ID = 32      # ✅ Employee
MANAGER_ID = 27       # ✅ Manager
HR_ID = 31            # ✅ HR (confirmed)
LEAVE_TYPE_ID = 1
YEAR = 2025


def fail(msg):
    print(f"\n❌ TEST FAILED: {msg}")
    sys.exit(1)


def ok(msg):
    print(f"✅ {msg}")


# =========================
# ✅ 1️⃣ CREATE WORKFLOW
# =========================
def test_create_workflow():
    print("\n--- Creating Leave Workflow ---")

    payload = {
        "name": "Leave Approval Flow",
        "module": "leave",
        "steps": [
            {"step_order": 1, "role": "manager", "is_final": False},
            {"step_order": 2, "role": "hr", "is_final": True}
        ]
    }

    r = requests.post(f"{BASE_URL}/workflow/create", json=payload)

    if r.status_code != 200:
        fail(f"Workflow creation failed → {r.text}")

    ok("Workflow created successfully")
    return r.json()["workflow_id"]


# =========================
# ✅ 2️⃣ INIT LEAVE BALANCE
# =========================
def test_init_balance():
    print("\n--- Initializing Leave Balance ---")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "leave_type_id": LEAVE_TYPE_ID,
        "year": YEAR,
        "quota": 10
    }

    r = requests.post(f"{BASE_URL}/hrms/leaves/balance/init", json=payload)

    if r.status_code != 200:
        fail(f"Leave balance init failed → {r.text}")

    ok("Leave balance initialized")


# =========================
# ✅ 3️⃣ APPLY LEAVE (SAFE FUTURE DATES ✅)
# =========================
def test_apply_leave():
    print("\n--- Applying Leave ---")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "leave_type_id": LEAVE_TYPE_ID,
        "start_date": "2025-12-20",
        "end_date": "2025-12-21",
        "total_days": 2,
        "reason": "Medical Test"
    }

    r = requests.post(f"{BASE_URL}/hrms/leaves/apply", json=payload)

    if r.status_code != 200:
        fail(f"Leave apply failed → {r.text}")

    leave_id = r.json()["data"]["leave_id"]
    ok(f"Leave applied successfully (leave_id={leave_id})")
    return leave_id


# =========================
# ✅ 4️⃣ VERIFY WORKFLOW AUTO START
# =========================
def test_workflow_started(leave_id):
    print("\n--- Checking Workflow Auto Start ---")

    r = requests.get(f"{BASE_URL}/workflow/leave/{leave_id}")

    if r.status_code != 200:
        fail("Workflow not started automatically")

    data = r.json()

    if data["status"]["status"] != "pending":
        fail("Workflow status is not pending")

    if len(data["history"]) != 1:
        fail("Workflow step 1 not created")

    ok("Workflow auto-start verified")


# =========================
# ✅ 5️⃣ MANAGER APPROVES
# =========================
def test_manager_approve(leave_id):
    print("\n--- Manager Approving ---")

    payload = {"remarks": "Approved by Manager"}
    r = requests.post(f"{BASE_URL}/workflow/leave/{leave_id}/approve", json=payload)

    if r.status_code != 200:
        fail(f"Manager approval failed → {r.text}")

    data = r.json()["next_step"]
    if data["role"] != "hr":
        fail("Workflow did not move to HR")

    ok("Manager approval successful → HR step created")


# =========================
# ✅ 6️⃣ HR APPROVES (FINAL)
# =========================
def test_hr_approve(leave_id):
    print("\n--- HR Approving (Final Step) ---")

    payload = {"remarks": "Approved by HR"}
    r = requests.post(f"{BASE_URL}/workflow/leave/{leave_id}/approve", json=payload)

    if r.status_code != 200:
        fail(f"HR approval failed → {r.text}")

    ok("HR final approval successful")


# =========================
# ✅ 7️⃣ VERIFY FINAL STATUS
# =========================
def test_leave_final_status(leave_id):
    print("\n--- Verifying Final Leave Status ---")

    r = requests.get(f"{BASE_URL}/hrms/leaves/requests")

    leave_rows = r.json()
    leave = next((l for l in leave_rows if l["leave_id"] == leave_id), None)

    if not leave:
        fail("Leave not found in request list")

    if leave["status"] != "approved":
        fail("Leave was NOT approved after final workflow step")

    ok("Leave final status is APPROVED ✅")


# =========================
# ✅ 8️⃣ TEST REJECT FLOW (SAFE DATES ✅)
# =========================
def test_reject_flow():
    print("\n--- Testing Reject Flow ---")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "leave_type_id": LEAVE_TYPE_ID,
        "start_date": "2025-12-25",
        "end_date": "2025-12-26",
        "total_days": 2,
        "reason": "Personal"
    }

    r = requests.post(f"{BASE_URL}/hrms/leaves/apply", json=payload)
    if r.status_code != 200:
        fail(f"Leave apply failed for reject test → {r.text}")

    leave_id = r.json()["data"]["leave_id"]
    ok(f"Reject Test Leave Applied (leave_id={leave_id})")

    payload = {"remarks": "Rejected for testing"}
    r = requests.post(f"{BASE_URL}/workflow/leave/{leave_id}/reject", json=payload)

    if r.status_code != 200:
        fail(f"Leave reject failed → {r.text}")

    r = requests.get(f"{BASE_URL}/hrms/leaves/requests")
    leave_rows = r.json()
    leave = next((l for l in leave_rows if l["leave_id"] == leave_id), None)

    if leave["status"] != "rejected":
        fail("Leave was NOT rejected")

    ok("Reject flow working ✅")


# =========================
# ✅ MAIN RUNNER
# =========================
if __name__ == "__main__":
    print("\n==============================")
    print("🚀 STARTING LEAVE WORKFLOW TEST")
    print("==============================")

    wf_id = test_create_workflow()
    time.sleep(1)

    test_init_balance()
    time.sleep(1)

    leave_id = test_apply_leave()
    time.sleep(1)

    test_workflow_started(leave_id)
    time.sleep(1)

    test_manager_approve(leave_id)
    time.sleep(1)

    test_hr_approve(leave_id)
    time.sleep(1)

    test_leave_final_status(leave_id)
    time.sleep(1)

    test_reject_flow()

    print("\n==============================")
    print("✅✅✅ ALL TESTS PASSED SUCCESSFULLY ✅✅✅")
    print("==============================")
