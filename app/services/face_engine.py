import cv2
import numpy as np
from insightface.app import FaceAnalysis

# =====================================================
# INIT INSIGHTFACE (ONCE)
# =====================================================
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))


# =====================================================
# CONFIG (REALISTIC DEFAULTS)
# =====================================================
MIN_FACE_SIZE = 120  # reject tiny / blurry faces
MATCH_THRESHOLD = 1.0  # L2 distance threshold (normalized embeddings)


# =====================================================
# EXTRACT EMBEDDING (NORMALIZED)
# =====================================================
def extract_embedding(image_bytes: bytes):
    """
    Extract face embedding from image bytes.
    - Picks largest face
    - Rejects small faces
    - Returns normalized embedding or None
    """
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        return None

    faces = face_app.get(img)
    if not faces:
        return None

    # -------------------------------------------------
    # Pick LARGEST face (CompreFace behavior)
    # -------------------------------------------------
    faces = sorted(
        faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True
    )

    face = faces[0]

    # -------------------------------------------------
    # Reject SMALL / LOW-QUALITY faces
    # -------------------------------------------------
    x1, y1, x2, y2 = face.bbox
    w, h = x2 - x1, y2 - y1

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return None

    # InsightFace embedding (512-d) ✅ NORMALIZED
    emb = face.embedding.astype("float32")
    emb /= np.linalg.norm(emb) + 1e-8
    return emb


# =====================================================
# VERIFY (1:1) — USING MEAN TEMPLATE
# =====================================================
def compare_embeddings(
    known_embeddings: list, unknown_embedding: np.ndarray, threshold: float = MATCH_THRESHOLD
):
    """
    Verify face against stored embeddings for ONE employee.
    Uses MEAN embedding (CompreFace-style).
    """
    if not known_embeddings:
        return False, None

    # ✅ Normalize all embeddings
    known = np.vstack([np.array(e, dtype="float32") for e in known_embeddings])
    known /= np.linalg.norm(known, axis=1, keepdims=True) + 1e-8

    unknown = np.array(unknown_embedding, dtype="float32")
    unknown /= np.linalg.norm(unknown) + 1e-8

    mean_embedding = known.mean(axis=0)
    mean_embedding /= np.linalg.norm(mean_embedding) + 1e-8

    distance = float(np.linalg.norm(mean_embedding - unknown))

    return distance < threshold, distance


# =====================================================
# IDENTIFY (1:N) — USING MEAN TEMPLATE
# =====================================================
def identify_face(
    all_faces: dict, unknown_embedding: np.ndarray, threshold: float = MATCH_THRESHOLD
):
    """
    Identify employee from face.
    all_faces = {
        employee_id: [embedding1, embedding2, ...]
    }
    """
    best_employee = None
    best_distance = float("inf")

    # ✅ Normalize query
    q = np.array(unknown_embedding, dtype="float32")
    q /= np.linalg.norm(q) + 1e-8

    for emp_id, embeddings in all_faces.items():
        if not embeddings:
            continue

        embs = np.vstack([np.array(e, dtype="float32") for e in embeddings])
        embs /= np.linalg.norm(embs, axis=1, keepdims=True) + 1e-8

        mean_embedding = embs.mean(axis=0)
        mean_embedding /= np.linalg.norm(mean_embedding) + 1e-8

        distance = float(np.linalg.norm(mean_embedding - q))

        if distance < best_distance:
            best_distance = distance
            best_employee = emp_id

    if best_employee is not None and best_distance < threshold:
        return {
            "match": True,
            "employee_id": best_employee,
            "distance": best_distance,
        }

    return {
        "match": False,
        "employee_id": None,
    }
