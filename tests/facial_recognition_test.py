import requests

BASE_URL = "http://localhost:8000"   # FastAPI backend
IMAGE_PATH = "test.jpg"              # SAME image used for registration

LATITUDE = 12.9716
LONGITUDE = 77.5946


def test_face_attendance():
    url = f"{BASE_URL}/faces/attendance"

    files = {
        "image": (
            "test.jpg",
            open(IMAGE_PATH, "rb"),
            "image/jpeg"
        )
    }

    data = {
        "latitude": str(LATITUDE),
        "longitude": str(LONGITUDE),
    }

    response = requests.post(url, files=files, data=data)

    print("STATUS CODE:", response.status_code)

    try:
        print("RESPONSE JSON:")
        print(response.json())
    except Exception:
        print("RAW RESPONSE:")
        print(response.text)


if __name__ == "__main__":
    test_face_attendance()
