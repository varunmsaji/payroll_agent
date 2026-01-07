import requests

BASE_URL = "http://localhost:8000"
IMAGE_PATH = "varun_image.jpeg"
EMPLOYEE_ID = "EMP001"


def register_face():
    url = f"{BASE_URL}/faces/register"

    files = {
        "image": ("varun.jpg", open(IMAGE_PATH, "rb"), "image/jpeg")
    }
    data = {"employee_id": EMPLOYEE_ID}

    resp = requests.post(url, files=files, data=data)

    print("\n=== REGISTER RESPONSE ===")
    print(resp.status_code)
    print(resp.json())


def recognize_face():
    url = f"{BASE_URL}/faces/recognize"

    files = {
        "image": ("varun.jpg", open(IMAGE_PATH, "rb"), "image/jpeg")
    }

    resp = requests.post(url, files=files)

    print("\n=== RECOGNIZE RESPONSE ===")
    print(resp.status_code)
    print(resp.json())


if __name__ == "__main__":
    # register_face()
    recognize_face()
