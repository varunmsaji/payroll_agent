import requests

BASE_URL = "http://localhost:8001"

IMAGE_PATH = "test.jpg"

# 🔹 Employee ID to register
EMPLOYEE_ID = "EMP001"


def register_face():
    url = f"{BASE_URL}/faces/register"

    files = {
        "image": open(IMAGE_PATH, "rb")
    }
    data = {
        "employee_id": EMPLOYEE_ID
    }

    resp = requests.post(url, files=files, data=data)

    print("\n=== REGISTER RESPONSE ===")
    print(resp.status_code)
    print(resp.json())


def recognize_face():
    url = f"{BASE_URL}/faces/recognize"

    files = {
        "image": open(IMAGE_PATH, "rb")
    }

    resp = requests.post(url, files=files)

    print("\n=== RECOGNIZE RESPONSE ===")
    print(resp.status_code)
    print(resp.json())


if __name__ == "__main__":
    register_face()
    recognize_face()
