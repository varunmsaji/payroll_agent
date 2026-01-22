import numpy as np
from app.database.connection import get_connection


# =====================================================
# INIT DB (RUN ON STARTUP)
# =====================================================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            employee_id TEXT NOT NULL,
            embedding BYTEA NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# =====================================================
# SAVE FACE (MULTIPLE PER EMPLOYEE)
# =====================================================
def save_face(employee_id: str, embedding: np.ndarray):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO faces (employee_id, embedding)
        VALUES (%s, %s)
        """,
        (
            employee_id,
            embedding.astype("float32").tobytes(),
        )
    )

    conn.commit()
    cur.close()
    conn.close()


# =====================================================
# GET FACES FOR ONE EMPLOYEE
# =====================================================
def get_faces(employee_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT embedding
        FROM faces
        WHERE employee_id = %s
        """,
        (employee_id,)
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        np.frombuffer(row["embedding"], dtype="float32")
        for row in rows
    ]


# =====================================================
# GET ALL FACES (FOR IDENTIFY)
# =====================================================
def get_all_faces():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT employee_id, embedding
        FROM faces
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    faces = {}

    for row in rows:
        emb = np.frombuffer(row["embedding"], dtype="float32")
        faces.setdefault(row["employee_id"], []).append(emb)

    return faces
