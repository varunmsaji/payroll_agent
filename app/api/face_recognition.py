from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import httpx

router = APIRouter(prefix="/faces", tags=["Faces"])

COMPRE_FACE_URL = "http://localhost:8000"
API_KEY = "788f96a2-f526-4ab0-83b1-2e8cecaa520b"
COLLECTION_ID = "b2f6dbb6-eca2-4472-a858-ac9cc67d4e34"


# 🔹 Register a new employee face
@router.post("/register")
async def register_face(
    employee_id: str = Form(...),
    image: UploadFile = File(...)
):
    if not API_KEY or not COLLECTION_ID:
        raise HTTPException(500, "CompreFace credentials not configured")

    # ✅ correct endpoint for CompreFace 1.2
    url = (
        f"{COMPRE_FACE_URL}/api/v1/recognition/faces"
        f"?collection_id={COLLECTION_ID}&subject={employee_id}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            headers={"x-api-key": API_KEY},
            files={"file": (image.filename, await image.read(), image.content_type)},
        )

    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)

    return {"message": "Face registered", "employee_id": employee_id, "data": r.json()}


# 🔹 Recognize an employee from a photo
@router.post("/recognize")
async def recognize_face(image: UploadFile = File(...)):
    if not API_KEY or not COLLECTION_ID:
        raise HTTPException(500, "CompreFace credentials not configured")

    url = (
        f"{COMPRE_FACE_URL}/api/v1/recognition/recognize"
        f"?collection_id={COLLECTION_ID}&limit=1"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            headers={"x-api-key": API_KEY},
            files={"file": (image.filename, await image.read(), image.content_type)},
        )

    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)

    data = r.json()

    results = data.get("result", [])
    if not results:
        return {"recognized": False}

    match = results[0]["subjects"][0]
    return {
        "recognized": True,
        "employee_id": match["subject"],
        "similarity": match["similarity"],
        "raw": data,
    }
