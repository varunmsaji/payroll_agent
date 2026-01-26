# app/services/attendance/policy.py

from dataclasses import dataclass
from datetime import date, datetime, time

from app.database.connection import get_connection


# =========================================================
# POLICY MODEL
# =========================================================
@dataclass(frozen=True)
class AttendancePolicy:
    late_grace_minutes: int
    early_exit_grace_minutes: int
    early_checkin_grace_minutes: int
    full_day_fraction: float
    half_day_fraction: float
    overtime_enabled: bool
    late_checkin_cutoff_minutes: int  # ⬅️ NEW (IMPORTANT)


# =========================================================
# POLICY DB ACCESS
# =========================================================
class AttendancePolicyDB:

    # ✅ SAFE DEFAULT (used if DB fails or empty)
    DEFAULT_POLICY = AttendancePolicy(
        late_grace_minutes=10,
        early_exit_grace_minutes=10,
        early_checkin_grace_minutes=0,
        full_day_fraction=0.75,
        half_day_fraction=0.5,
        overtime_enabled=True,
        late_checkin_cutoff_minutes=0,  # ⬅️ BLOCK check-in after shift
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
                    overtime_enabled,
                    COALESCE(late_checkin_cutoff_minutes, 0)
                FROM attendance_policies
                WHERE created_at <= %s
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (end_of_day,),
            )

            row = cur.fetchone()
            cur.close()

            # 🛑 No policy found → fallback
            if not row:
                return AttendancePolicyDB.DEFAULT_POLICY

            return AttendancePolicy(
                late_grace_minutes=int(row[0]),
                early_exit_grace_minutes=int(row[1]),
                early_checkin_grace_minutes=int(row[2]),
                full_day_fraction=float(row[3]),
                half_day_fraction=float(row[4]),
                overtime_enabled=bool(row[5]),
                late_checkin_cutoff_minutes=int(row[6]),
            )

        except Exception:
            # 🔥 Never break attendance due to policy error
            return AttendancePolicyDB.DEFAULT_POLICY

        finally:
            if conn:
                conn.close()
