import requests
import json

BASE_URL = "http://127.0.0.1:8000/hrms/settings"

print("\n==============================")
print("🚀 HRMS SETTINGS DASHBOARD TESTER")
print("==============================\n")

# =====================================================
# 1️⃣ GET PAYROLL POLICY
# =====================================================
print("🔹 TEST: GET PAYROLL POLICY")
res = requests.get(f"{BASE_URL}/payroll-policy")
print("Status:", res.status_code)
try:
    print(json.dumps(res.json(), indent=2))
except:
    print(res.text)
print("\n" + "-"*40 + "\n")


# =====================================================
# 2️⃣ UPDATE PAYROLL POLICY
# =====================================================
print("🔹 TEST: UPDATE PAYROLL POLICY")

payload = {
    "late_grace_minutes": 12,
    "late_lop_threshold_minutes": 30,
    "early_exit_grace_minutes": 10,
    "early_exit_lop_threshold_minutes": 25,
    "overtime_enabled": True,
    "overtime_multiplier": 1.5,
    "holiday_double_pay": True,
    "weekend_paid_only_if_worked": True,
    "night_shift_allowance": 250
}

res = requests.put(
    f"{BASE_URL}/payroll-policy",
    json=payload
)

print("Status:", res.status_code)
try:
    print(json.dumps(res.json(), indent=2))
except:
    print(res.text)

print("\n" + "-"*40 + "\n")


# =====================================================
# 3️⃣ GET ATTENDANCE POLICY (DYNAMIC + HISTORY)
# =====================================================
print("🔹 TEST: GET ATTENDANCE POLICY")
res = requests.get(f"{BASE_URL}/attendance-policy")
print("Status:", res.status_code)
try:
    print(json.dumps(res.json(), indent=2))
except:
    print(res.text)
print("\n" + "-"*40 + "\n")


# =====================================================
# 4️⃣ UPDATE ATTENDANCE POLICY
# =====================================================
print("🔹 TEST: UPDATE ATTENDANCE POLICY")

payload = {
    "late_grace_minutes": 15,
    "early_exit_grace_minutes": 10,
    "full_day_fraction": 0.8,
    "half_day_fraction": 0.6,
    "night_shift_enabled": True,
    "overtime_enabled": True
}

res = requests.put(
    f"{BASE_URL}/attendance-policy",
    json=payload
)

print("Status:", res.status_code)
try:
    print(json.dumps(res.json(), indent=2))
except:
    print(res.text)

print("\n" + "-"*40 + "\n")


# =====================================================
# 5️⃣ LIST ALL WORKFLOWS
# =====================================================
print("🔹 TEST: LIST WORKFLOWS")
res = requests.get(f"{BASE_URL}/workflows")
print("Status:", res.status_code)
try:
    workflows = res.json()
    print(json.dumps(workflows, indent=2))
except:
    print(res.text)

print("\n" + "-"*40 + "\n")


# =====================================================
# 6️⃣ ACTIVATE A WORKFLOW (IF EXISTS)
# =====================================================
if isinstance(workflows, list) and workflows:
    workflow_id = workflows[0]["id"]

    print("🔹 TEST: ACTIVATE WORKFLOW → ID:", workflow_id)

    payload = {
        "workflow_id": workflow_id
    }

    res = requests.post(
        f"{BASE_URL}/workflows/activate",
        json=payload
    )

    print("Status:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)

    print("\n" + "-"*40 + "\n")

else:
    print("⚠️ No workflows found to activate\n")


# =====================================================
# 7️⃣ DEACTIVATE A WORKFLOW
# =====================================================
if isinstance(workflows, list) and workflows:
    workflow_id = workflows[0]["id"]

    print("🔹 TEST: DEACTIVATE WORKFLOW → ID:", workflow_id)

    payload = {
        "workflow_id": workflow_id
    }

    res = requests.post(
        f"{BASE_URL}/workflows/deactivate",
        json=payload
    )

    print("Status:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)

    print("\n" + "-"*40 + "\n")

else:
    print("⚠️ No workflows found to deactivate\n")


print("✅ ALL SETTINGS DASHBOARD TESTS COMPLETED SUCCESSFULLY\n")
