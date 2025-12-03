import requests
import json
import time

BASE_URL = "http://localhost:8000"

# -------------------------------
# 🔹 ✅ UPDATED CONFIG (FROM YOUR DB)
# -------------------------------
EMPLOYEE_ID = 33        # ✅ Anita Shetty
MANAGER_ID  = 32        # ✅ Sneha Gupta (Manager)
LEAVE_REQUEST_ID = 101  # ⚠️ MUST EXIST in leave_requests table


# -------------------------------
# ✅ 1️⃣ LIST ALL WORKFLOWS
# -------------------------------
def list_workflows():
    print("\n📌 Listing all workflows...")
    r = requests.get(f"{BASE_URL}/workflow/all")
    print(r.status_code, json.dumps(r.json(), indent=2))
    return r.json()


# -------------------------------
# ✅ 2️⃣ CREATE LEAVE WORKFLOW (IF NONE EXISTS)
# -------------------------------
def create_leave_workflow():
    print("\n🛠 Creating leave workflow...")
    payload = {
        "name": "Leave Manager → HR",
        "module": "leave",
        "steps": [
            {"step_order": 1, "role": "manager", "is_final": False},
            {"step_order": 2, "role": "hr", "is_final": True}
        ]
    }

    r = requests.post(
        f"{BASE_URL}/workflow/create",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    print(r.status_code, r.json())
    return r.json()["workflow_id"]


# -------------------------------
# ✅ 3️⃣ ACTIVATE WORKFLOW
# -------------------------------
def activate_workflow(workflow_id):
    print(f"\n✅ Activating workflow ID {workflow_id}...")
    r = requests.post(f"{BASE_URL}/workflow/activate/{workflow_id}")
    print(r.status_code, r.json())


# -------------------------------
# ✅ 4️⃣ GET ACTIVE WORKFLOW (FIXES 404)
# -------------------------------
def get_active_leave_workflow():
    print("\n👀 Fetching active leave workflow...")
    r = requests.get(f"{BASE_URL}/workflow/active/leave")
    print(r.status_code, json.dumps(r.json(), indent=2))


# -------------------------------
# ✅ 5️⃣ START WORKFLOW FOR LEAVE REQUEST
# -------------------------------
def start_leave_workflow():
    print("\n🚀 Starting workflow for leave request...")
    payload = {
        "employee_id": EMPLOYEE_ID
    }

    r = requests.post(
        f"{BASE_URL}/workflow/leave/start/{LEAVE_REQUEST_ID}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    print(r.status_code, r.json())


# -------------------------------
# ✅ 6️⃣ CHECK WORKFLOW STATUS
# -------------------------------
def get_workflow_status():
    print("\n📊 Checking workflow status...")
    r = requests.get(f"{BASE_URL}/workflow/leave/{LEAVE_REQUEST_ID}")
    print(r.status_code, json.dumps(r.json(), indent=2))


# -------------------------------
# ✅ 7️⃣ APPROVER INBOX (MANAGER VIEW)
# -------------------------------
def approver_inbox():
    print("\n📥 Fetching approver inbox for manager...")
    r = requests.get(f"{BASE_URL}/workflow/pending/{MANAGER_ID}")
    print(r.status_code, json.dumps(r.json(), indent=2))


# -------------------------------
# ✅ 8️⃣ APPROVE REQUEST (MANAGER STEP)
# -------------------------------
def approve_leave():
    print("\n✅ Approving leave request as MANAGER...")
    payload = {
        "approver_id": MANAGER_ID,
        "remarks": "Approved by manager via Python test"
    }

    r = requests.post(
        f"{BASE_URL}/workflow/leave/{LEAVE_REQUEST_ID}/approve",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    print(r.status_code, json.dumps(r.json(), indent=2))


# -------------------------------
# ✅ 9️⃣ (OPTIONAL) REJECT REQUEST TEST
# -------------------------------
def reject_leave():
    print("\n❌ Rejecting leave request...")
    payload = {
        "approver_id": MANAGER_ID,
        "remarks": "Rejected via Python test"
    }

    r = requests.post(
        f"{BASE_URL}/workflow/leave/{LEAVE_REQUEST_ID}/reject",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    print(r.status_code, r.json())


# -------------------------------
# ✅ 🔟 DELETE WORKFLOW (ADMIN)
# -------------------------------
def delete_workflow(workflow_id):
    print(f"\n🗑 Deleting workflow ID {workflow_id}...")
    r = requests.delete(f"{BASE_URL}/workflow/{workflow_id}")
    print(r.status_code, r.json())


# -------------------------------
# 🚀 ✅ RUN FULL TEST SEQUENCE
# -------------------------------
if __name__ == "__main__":
    print("\n==============================")
    print("✅ WORKFLOW SYSTEM TEST START")
    print("==============================")

    workflows = list_workflows()

    # Pick latest workflow or create a new one
    if not workflows:
        workflow_id = create_leave_workflow()
    else:
        workflow_id = workflows[0]["id"]

    activate_workflow(workflow_id)

    get_active_leave_workflow()

    start_leave_workflow()

    time.sleep(1)

    get_workflow_status()

    approver_inbox()

    approve_leave()

    time.sleep(1)

    get_workflow_status()

    print("\n==============================")
    print("✅ WORKFLOW SYSTEM TEST COMPLETE")
    print("==============================")
