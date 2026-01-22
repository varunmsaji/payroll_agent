import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Initialize InsightFace once (important)
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))


def extract_embedding(image_bytes: bytes):
    """
    Extract face embedding from image bytes.
    Returns numpy array or None.
    """
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        return None

    faces = face_app.get(img)
    if not faces:
        return None

    return faces[0].embedding


def compare_embeddings(
    known_embeddings: list,
    unknown_embedding: np.ndarray,
    threshold: float = 0.6
):
    """
    Compare unknown face against multiple stored embeddings.
    Returns (match: bool, best_distance: float)
    """
    best_distance = float("inf")

    for emb in known_embeddings:
        dist = float(np.linalg.norm(emb - unknown_embedding))
        if dist < best_distance:
            best_distance = dist

    match = bool(best_distance < threshold)
    return match, best_distance



def identify_face(
    all_faces: dict,
    unknown_embedding: np.ndarray,
    threshold: float = 0.6
):
    """
    all_faces = {
        employee_id: [embedding1, embedding2, ...]
    }
    """
    best_employee = None
    best_distance = float("inf")

    for emp_id, embeddings in all_faces.items():
        for emb in embeddings:
            dist = float(np.linalg.norm(emb - unknown_embedding))
            if dist < best_distance:
                best_distance = dist
                best_employee = emp_id

    if best_employee and best_distance < threshold:
        return {
            "match": True,
            "employee_id": best_employee,
            "distance": best_distance
        }

    return {
        "match": False,
        "employee_id": None
    }
