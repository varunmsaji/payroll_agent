# app/database/shifts_db.py

from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection


class ShiftDB:

    # ============================
    # ✅ CREATE SHIFT (SAFE)
    # ============================
    @staticmethod
    def add_shift(data):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Prevent duplicate active shift names
                cur.execute(
                    """
                    SELECT 1
                    FROM shifts
                    WHERE shift_name = %s
                      AND is_active = TRUE;
                    """,
                    (data["shift_name"],),
                )
                if cur.fetchone():
                    raise Exception("Shift name already exists")

                cur.execute(
                    """
                    INSERT INTO shifts
                    (shift_name, start_time, end_time, is_night_shift,
                     break_start, break_end, break_minutes, is_active)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE)
                    RETURNING *;
                    """,
                    (
                        data["shift_name"],
                        data["start_time"],
                        data["end_time"],
                        data.get("is_night_shift", False),
                        data.get("break_start"),
                        data.get("break_end"),
                        data.get("break_minutes", 0),
                    ),
                )

                return cur.fetchone()

    # ============================
    # ✅ LIST SHIFTS (PAGINATED)
    # ============================
    @staticmethod
    def get_all(page: int = 1, limit: int = 20):
        offset = (page - 1) * limit

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM shifts
                    WHERE is_active = TRUE
                    ORDER BY shift_id DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (limit, offset),
                )
                return cur.fetchall()

    # ============================
    # ✅ GET ONE SHIFT
    # ============================
    @staticmethod
    def get_one(shift_id: int):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM shifts
                    WHERE shift_id = %s
                      AND is_active = TRUE;
                    """,
                    (shift_id,),
                )
                return cur.fetchone()

    # ============================
    # ✅ UPDATE SHIFT
    # ============================
    @staticmethod
    def update_shift(shift_id: int, data):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE shifts
                    SET
                        shift_name     = %s,
                        start_time     = %s,
                        end_time       = %s,
                        is_night_shift = %s,
                        break_start    = %s,
                        break_end      = %s,
                        break_minutes  = %s
                    WHERE shift_id = %s
                      AND is_active = TRUE
                    RETURNING *;
                    """,
                    (
                        data["shift_name"],
                        data["start_time"],
                        data["end_time"],
                        data.get("is_night_shift", False),
                        data.get("break_start"),
                        data.get("break_end"),
                        data.get("break_minutes", 0),
                        shift_id,
                    ),
                )

                return cur.fetchone()

    # ============================
    # ✅ SOFT DELETE SHIFT
    # ============================
    @staticmethod
    def delete_shift(shift_id: int) -> bool:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE shifts
                    SET is_active = FALSE
                    WHERE shift_id = %s
                    RETURNING shift_id;
                    """,
                    (shift_id,),
                )
                return bool(cur.fetchone())
