# app/services/attendance/policy.py

from dataclasses import dataclass
from datetime import datetime, date, time

from app.database.connection import get_connection


@dataclass(frozen=True)
class AttendancePolicy:
    late_grace_minutes: int
    early_exit_grace_minutes: int
    early_checkin_grace_minutes: int
    full_day_fraction: float
    half_day_fraction: float
    overtime_enabled: bool


class AttendancePolicyDB:
    DEFAULT_POLICY = AttendancePolicy(
        late_grace_minutes=10,
        early_exit_grace_minutes=10,
        early_checkin_grace_minutes=0,
        full_day_fraction=0.75,
        half_day_fraction=0.5,
        overtime_enabled=True,
    )

    @staticmethod
    def get_policy_for_date(dt: date) -> AttendancePolicy:
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            end_of_day = datetime.combine(dt, time(23, 59, 59))

            cur.execute(
                """
                SELECT
                    late_grace_minutes,
                    early_exit_grace_minutes,
                    early_checkin_grace_minutes,
                    full_day_fraction,
                    half_day_fraction,
                    overtime_enabled
                FROM attendance_policies
                WHERE created_at <= %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (end_of_day,),
            )

            row = cur.fetchone()
            cur.close()

            if not row:
                return AttendancePolicyDB.DEFAULT_POLICY

            return AttendancePolicy(
                int(row[0]),
                int(row[1]),
                int(row[2]),
                float(row[3]),
                float(row[4]),
                bool(row[5]),
            )

        except Exception:
            return AttendancePolicyDB.DEFAULT_POLICY

        finally:
            if conn:
                conn.close()
