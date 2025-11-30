import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def pretty_print(title, resp):
    print("\n" + "=" * 70)
    print(f"🔹 {title}")
    print(f"Status Code: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except Exception:
        print("Raw Response:", resp.text)
    print("=" * 70)


if __name__ == "__main__":
    print("🚀 Testing Payroll Policy API")

    # ✅ Fetch Active Payroll Policy
    url = f"{BASE_URL}/hrms/payroll/policy"
    response = requests.get(url)

    pretty_print("Get Active Payroll Policy", response)
