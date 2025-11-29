# app/database/shifts_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection


class ShiftDB:

    # ============================
    # ✅ CREATE SHIFT (SAFE)
    # ============================
    @staticmethod
    def add_shift(data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ✅ Prevent duplicate shift names
        cur.execute("SELECT 1 FROM shifts WHERE shift_name=%s AND is_active=true;", (data["shift_name"],))
        if cur.fetchone():
            conn.close()
            raise Exception("Shift name already exists")

        cur.execute("""
            INSERT INTO shifts
            (shift_name, start_time, end_time, is_night_shift,
             break_start, break_end, break_minutes, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,true)
            RETURNING *;
        """, (
            data["shift_name"],
            data["start_time"],
            data["end_time"],
            data.get("is_night_shift", False),
            data.get("break_start"),
            data.get("break_end"),
            data.get("break_minutes", 0)
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    # ============================
    # ✅ LIST SHIFTS (PAGINATED)
    # ============================
    @staticmethod
    def get_all(page=1, limit=20):
        offset = (page - 1) * limit
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM shifts
            WHERE is_active=true
            ORDER BY shift_id DESC
            LIMIT %s OFFSET %s;
        """, (limit, offset))

        rows = cur.fetchall()
        conn.close()
        return rows

    # ============================
    # ✅ GET ONE
    # ============================
    @staticmethod
    def get_one(shift_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM shifts
            WHERE shift_id=%s AND is_active=true;
        """, (shift_id,))

        res = cur.fetchone()
        conn.close()
        return res

    # ============================
    # ✅ UPDATE SHIFT (SAFE)
    # ============================
    @staticmethod
    def update_shift(shift_id, data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE shifts
            SET shift_name=%s, start_time=%s, end_time=%s, is_night_shift=%s,
                break_start=%s, break_end=%s, break_minutes=%s
            WHERE shift_id=%s AND is_active=true
            RETURNING *;
        """, (
            data["shift_name"],
            data["start_time"],
            data["end_time"],
            data.get("is_night_shift", False),
            data.get("break_start"),
            data.get("break_end"),
            data.get("break_minutes", 0),
            shift_id
        ))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return res

    # ============================
    # ✅ SOFT DELETE SHIFT
    # ============================
    @staticmethod
    def delete_shift(shift_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE shifts
            SET is_active=false
            WHERE shift_id=%s
            RETURNING shift_id;
        """, (shift_id,))

        res = cur.fetchone()
        conn.commit()
        conn.close()
        return True if res else False
