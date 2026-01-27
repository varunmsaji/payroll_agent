# app/services/attendence/engine.py

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


class AttendanceEngine:

    def __init__(self, policy):
        self.policy = policy

    # -------------------------------------------------
    # WORK + BREAK
    # -------------------------------------------------
    def compute_work_and_breaks(self, events):
    # ✅ DEFENSIVE: ensure chronological order
        events = sorted(events, key=lambda e: e["event_time"])

        work_sec = 0
        break_sec = 0
        last_work_start = None
        last_break_start = None
        check_in = None
        check_out = None

        for ev in events:
            t = ev["event_time"]
            et = ev["event_type"]

            if et == "check_in":
                check_in = t
                last_work_start = t

            elif et == "break_start" and last_work_start:
                work_sec += (t - last_work_start).total_seconds()
                last_work_start = None
                last_break_start = t

            elif et == "break_end" and last_break_start:
                break_sec += (t - last_break_start).total_seconds()
                last_break_start = None
                last_work_start = t

            elif et == "check_out":
                check_out = t
                if last_work_start:
                    work_sec += (t - last_work_start).total_seconds()

        return work_sec, break_sec, check_in, check_out


    # -------------------------------------------------
    # LATE
    # -------------------------------------------------
    def compute_late(self, shift, dt, actual_in):
        if not shift or not actual_in:
            return 0, False

        shift_start = datetime.combine(dt, shift["start_time"])
        shift_start = shift_start.replace(tzinfo=IST).astimezone(UTC)

        late_minutes = int((actual_in - shift_start).total_seconds() / 60)
        grace = shift.get("late_grace_minutes", 0)

        if late_minutes > grace:
            return late_minutes - grace, True

        return 0, False

    # -------------------------------------------------
    # EARLY EXIT
    # -------------------------------------------------
    def compute_early(self, shift, dt, actual_out):
        if not shift or not actual_out:
            return 0, False

        start = shift["start_time"]
        end = shift["end_time"]

        if shift.get("is_night_shift") or end <= start:
            shift_end = datetime.combine(dt + timedelta(days=1), end)
        else:
            shift_end = datetime.combine(dt, end)

        shift_end = shift_end.replace(tzinfo=IST).astimezone(UTC)

        early_minutes = int((shift_end - actual_out).total_seconds() / 60)
        grace = self.policy.early_exit_grace_minutes or 0

        if early_minutes > grace:
            return early_minutes - grace, True

        return 0, False

    # -------------------------------------------------
    # ✅ OVERTIME (🔥 REQUIRED FIX)
    # -------------------------------------------------
    def compute_overtime(self, actual_out, shift_end, late_minutes):
        if not actual_out or actual_out <= shift_end:
            return 0, False

        if not getattr(self.policy, "overtime_enabled", True):
            return 0, False

        overtime = int((actual_out - shift_end).total_seconds() / 60)

        # Optional: deduct late minutes
        overtime = max(0, overtime - late_minutes)

        return overtime, overtime > 0

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------
    def decide_status(self, net_hours, required_hours):
        if net_hours >= required_hours * self.policy.full_day_fraction:
            return "present"
        if net_hours >= required_hours * self.policy.half_day_fraction:
            return "half_day"
        return "short_hours"
