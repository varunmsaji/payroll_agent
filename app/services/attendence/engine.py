# app/services/attendance/engine.py

from datetime import datetime, timedelta


class AttendanceEngine:
    def __init__(self, policy):
        self.policy = policy

    def compute_work_and_breaks(self, events, shift, dt):
        """
        Computes:
        - total work seconds
        - total break seconds
        - normalized check_in
        - check_out

        Applies early check-in policy correctly
        """

        work_sec = 0
        break_sec = 0

        last_work_start = None
        last_break_start = None

        check_in = None
        check_out = None

        # --------------------------------------------------
        # Shift start reference
        # --------------------------------------------------
        shift_start = None
        if shift and shift.get("start_time"):
            shift_start = datetime.combine(dt, shift["start_time"])

        for ev in events:
            t = ev["event_time"]
            et = ev["event_type"]

            # -------------------------
            # CHECK-IN
            # -------------------------
            if et == "check_in":

                normalized_time = t

                # Handle early check-in
                if shift_start and t < shift_start:
                    grace = self.policy.early_checkin_grace_minutes
                    action = self.policy.early_checkin_action

                    diff_minutes = int((shift_start - t).total_seconds() / 60)

                    # Beyond grace window
                    if diff_minutes > grace:
                        if action == "block":
                            raise Exception("Early check-in not allowed")

                        elif action == "ignore":
                            continue  # Do not start work

                        elif action == "cap":
                            normalized_time = shift_start
                        # allow → keep original t

                check_in = normalized_time
                last_work_start = normalized_time

            # -------------------------
            # BREAK START
            # -------------------------
            elif et == "break_start" and last_work_start:
                work_sec += (t - last_work_start).total_seconds()
                last_break_start = t
                last_work_start = None

            # -------------------------
            # BREAK END
            # -------------------------
            elif et == "break_end" and last_break_start:
                break_sec += (t - last_break_start).total_seconds()
                last_work_start = t
                last_break_start = None

            # -------------------------
            # CHECK-OUT
            # -------------------------
            elif et == "check_out":
                check_out = t
                if last_work_start:
                    work_sec += (t - last_work_start).total_seconds()
                    last_work_start = None

        return work_sec, break_sec, check_in, check_out

    def compute_late(self, shift, dt, actual_in):
        if not shift or not actual_in:
            return 0, False

        shift_start = datetime.combine(dt, shift["start_time"])
        late_minutes = int((actual_in - shift_start).total_seconds() / 60)

        return (
            (late_minutes, True)
            if late_minutes > self.policy.late_grace_minutes
            else (0, False)
        )

    def compute_early(self, shift, dt, actual_out):
        if not shift or not actual_out:
            return 0, False

        end = shift["end_time"]
        is_night = shift.get("is_night_shift", False)

        shift_end = (
            datetime.combine(dt + timedelta(days=1), end)
            if is_night or end <= shift["start_time"]
            else datetime.combine(dt, end)
        )

        early_minutes = int((shift_end - actual_out).total_seconds() / 60)

        return (
            (early_minutes, True)
            if early_minutes > self.policy.early_exit_grace_minutes
            else (0, False)
        )

    def compute_overtime(self, actual_out, shift_end, late_minutes):
        if not self.policy.overtime_enabled:
            return 0, False

        if not actual_out or actual_out <= shift_end:
            return 0, False

        overtime = int((actual_out - shift_end).total_seconds() / 60)
        overtime -= late_minutes

        return (overtime, True) if overtime > 0 else (0, False)

    def decide_status(self, net_hours, required_hours):
        if net_hours >= required_hours * self.policy.full_day_fraction:
            return "present"
        if net_hours >= required_hours * self.policy.half_day_fraction:
            return "half_day"
        return "short_hours"
