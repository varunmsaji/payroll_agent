# app/database/shift_db.py

from psycopg2.extras import RealDictCursor
from .connection import get_connection


class ShiftDB:

    @staticmethod
    def add_shift(data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO shifts
            (shift_name, start_time, end_time, is_night_shift, break_start, break_end, break_minutes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
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

    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM shifts ORDER BY shift_id DESC;")
        res = cur.fetchall()
        conn.close()
        return res

    @staticmethod
    def get_one(shift_id):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM shifts WHERE shift_id=%s;", (shift_id,))
        res = cur.fetchone()
        conn.close()
        return res

    @staticmethod
    def update_shift(shift_id, data):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            UPDATE shifts
            SET shift_name=%s, start_time=%s, end_time=%s, is_night_shift=%s,
                break_start=%s, break_end=%s, break_minutes=%s
            WHERE shift_id=%s
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

    @staticmethod
    def delete_shift(shift_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM shifts
            WHERE shift_id=%s
            RETURNING shift_id;
        """, (shift_id,))
        res = cur.fetchone()
        conn.commit()
        conn.close()
        return True if res else False
