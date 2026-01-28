from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from app.database.attendence import AttendanceDB, AttendanceEventDB, HolidayDB, ShiftDB
from app.services.attendence.engine import AttendanceEngine
from app.services.attendence.exceptions import AttendanceRejected
from app.services.attendence.policy import AttendancePolicyDB
import math
IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


class AttendanceService:

    # ==================================================
    # MAIN ENTRY
    # ==================================================
    @classmethod
    def process_punch(
        cls,
        employee_id: int,
        event_time: datetime,
        source: str,
        meta: Optional[Dict[str, Any]] = None,
    ):
        meta = meta or {}

        if event_time.tzinfo is None:
            raise AttendanceRejected("event_time must include timezone")

        # -------------------------------------------------
        # NORMALIZE TIME
        # -------------------------------------------------
        event_time = event_time.astimezone(UTC)
        dt_local = event_time.astimezone(IST).date()

        # -------------------------------------------------
        # DUPLICATE PUNCH (30s)
        # -------------------------------------------------
        if AttendanceEventDB.exists_recent_event(employee_id, event_time, 30):
            return {"ignored": True, "reason": "duplicate_punch"}

        policy = AttendancePolicyDB.get_policy_for_date(dt_local)
        shift = ShiftDB.get_employee_shift(employee_id, dt_local)

        events = cls._get_session_events(employee_id, dt_local)
        state = cls._derive_state(events)

        # -------------------------------------------------
        # SHIFT WINDOW
        # -------------------------------------------------
        if not shift:
            raise AttendanceRejected("No active shift assigned")

        shift_start = datetime.combine(
            dt_local, shift["start_time"]
        ).replace(tzinfo=IST).astimezone(UTC)

        shift_end = datetime.combine(
            dt_local, shift["end_time"]
        ).replace(tzinfo=IST).astimezone(UTC)

        if shift_end <= shift_start:
            shift_end += timedelta(days=1)

        # -------------------------------------------------
        # EARLY CHECK-IN HANDLING
        # -------------------------------------------------
        if not state["checked_in"] and event_time < shift_start:
            early_minutes = math.ceil(
                (shift_start - event_time).total_seconds() / 60
            )

            grace = int(shift.get("early_overtime_grace_minutes", 0))
            max_early = int(shift.get("early_overtime_max_minutes", 0))

            if early_minutes <= grace:
                pass  # allowed

            elif early_minutes <= grace + max_early:
                if not shift.get("allow_early_overtime", False):
                    raise AttendanceRejected("Early check-in not allowed")

                overtime_minutes = early_minutes - grace

                if shift.get("early_overtime_requires_approval", False):
                    meta["early_overtime_pending"] = True
                    meta["early_overtime_minutes"] = overtime_minutes

            else:
                raise AttendanceRejected(
                    f"Early check-in too early (max {grace + max_early} minutes allowed)"
                )

        # -------------------------------------------------
        # LATE CHECK-IN HANDLING
        # -------------------------------------------------
        late_grace = int(shift.get("late_grace_minutes", 0))
        latest_allowed = shift_start + timedelta(minutes=late_grace)

        if (
            not state["checked_in"]
            and event_time >= shift_start
            and event_time > latest_allowed
        ):
            raise AttendanceRejected(
                f"Late check-in not allowed after "
                f"{latest_allowed.astimezone(IST).strftime('%H:%M')}"
            )

        # -------------------------------------------------
        # BREAK FSM v1
        # -------------------------------------------------
        break_start_time = shift.get("break_start")
        break_end_time = shift.get("break_end")
        break_grace = int(shift.get("break_grace_minutes", 0))

        break_window_start = break_window_end = None

        if break_start_time and break_end_time:
            bw_start = datetime.combine(dt_local, break_start_time)
            bw_end = datetime.combine(dt_local, break_end_time)

            break_window_start = (
                bw_start - timedelta(minutes=break_grace)
            ).replace(tzinfo=IST).astimezone(UTC)

            break_window_end = (
                bw_end + timedelta(minutes=break_grace)
            ).replace(tzinfo=IST).astimezone(UTC)

        # -------------------------------------------------
        # FSM DECISION
        # -------------------------------------------------
        if not state["checked_in"]:
            action = "check_in"

        elif state["checked_in"] and not state["on_break"]:
            # Possible break start
            if (
                break_window_start
                and break_window_end
                and break_window_start <= event_time <= break_window_end
            ):
                action = "break_start"

            elif event_time >= shift_end:
                action = "check_out"

            else:
                raise AttendanceRejected("Invalid punch sequence")

        elif state["on_break"]:
            if (
                break_window_start
                and break_window_end
                and break_window_start <= event_time <= break_window_end
            ):
                action = "break_end"
            else:
                raise AttendanceRejected("Break end outside allowed window")

        else:
            raise AttendanceRejected("Invalid attendance state")

        # -------------------------------------------------
        # SAVE EVENT
        # -------------------------------------------------
        AttendanceEventDB.add_event(
            employee_id=employee_id,
            event_type=action,
            source=source,
            meta=meta,
            event_time=event_time,
        )

        cls.recalculate_for_date(employee_id, dt_local)

        return {"action": action}



    # ==================================================
    # RE-CALCULATION (PAYROLL LOGIC)
    # ==================================================
    @classmethod
    def recalculate_for_date(cls, employee_id: int, dt: date):
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        engine = AttendanceEngine(policy)

        shift = ShiftDB.get_employee_shift(employee_id, dt)
        ws_local, we_local, required_hours, is_night, shift_id = cls._get_shift_window(
            shift, dt
        )

        ws = ws_local.replace(tzinfo=IST).astimezone(UTC)
        we = we_local.replace(tzinfo=IST).astimezone(UTC)

        start, end = cls._get_attendance_window(employee_id, dt)

        events = AttendanceEventDB.get_events_for_window(employee_id, start, end)

        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        # -------------------------------------------------
        # 🔥 BREAK VIOLATION HANDLING (SHORT HOURS)
        # -------------------------------------------------
        break_violation_minutes = 0

        if shift and shift.get("break_required"):
            b_start = shift.get("break_start")
            b_end = shift.get("break_end")
            grace = int(shift.get("break_grace_minutes", 0))

            if b_start and b_end:
                required_break = (
                    datetime.combine(dt, b_end)
                    - datetime.combine(dt, b_start)
                ).total_seconds() / 60

                required_break += grace

                actual_break = break_sec / 60

                if actual_break < required_break:
                    break_violation_minutes = int(required_break - actual_break)

        # -------------------------------------------------
        # HOURS CALCULATION
        # -------------------------------------------------
        total_hours = (work_sec + break_sec) / 3600
        net_hours = work_sec / 3600

        if break_violation_minutes > 0 and shift.get("break_violation_action") == "short_hours":
            penalty_hours = break_violation_minutes / 60
            net_hours = max(0, net_hours - penalty_hours)
            total_hours = max(0, total_hours - penalty_hours)

        total_hours = round(total_hours, 2)
        net_hours = round(net_hours, 2)

        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, is_early_checkout = engine.compute_early(shift, dt, check_out)

        overtime_minutes, is_overtime = engine.compute_overtime(
            actual_out=check_out,
            shift_end=we,
            late_minutes=late_minutes,
        )

        status = engine.decide_status(net_hours, required_hours)

        AttendanceDB.upsert_full_attendance(
            {
                "employee_id": employee_id,
                "shift_id": shift_id,
                "date": dt,
                "check_in": check_in,
                "check_out": check_out,
                "total_hours": total_hours,
                "net_hours": net_hours,
                "break_minutes": int(break_sec / 60),
                "late_minutes": late_minutes,
                "early_exit_minutes": early_minutes,
                "overtime_minutes": overtime_minutes,
                "is_overtime": is_overtime,
                "is_late": is_late,
                "is_early_checkout": is_early_checkout,
                "is_weekend": dt.weekday() >= 5,
                "is_holiday": HolidayDB.is_holiday(dt),
                "is_night_shift": is_night,
                "status": status,
                "is_payroll_locked": False,
                "locked_at": None,
            }
        )

    # ==================================================
    # HELPERS
    # ==================================================
    @classmethod
    def _get_attendance_window(cls, employee_id: int, dt: date):
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        shift = ShiftDB.get_employee_shift(employee_id, dt)

        ws_local, we_local, *_ = cls._get_shift_window(shift, dt)

        ws = ws_local.replace(tzinfo=IST).astimezone(UTC)
        we = we_local.replace(tzinfo=IST).astimezone(UTC)

        early_policy_grace = int(getattr(policy, "early_checkin_grace_minutes", 0))

        early_ot_grace = int(shift.get("early_overtime_grace_minutes", 0)) if shift else 0
        early_ot_max = int(shift.get("early_overtime_max_minutes", 0)) if shift else 0

        total_early_window = early_policy_grace + early_ot_grace + early_ot_max

        late_exit_grace = int(getattr(policy, "early_exit_grace_minutes", 0))

        return (
            ws - timedelta(minutes=total_early_window),
            we + timedelta(minutes=late_exit_grace),
        )


    @staticmethod
    def _derive_state(events):
        state = {"checked_in": False, "on_break": False}

        for e in events:
            if e["event_type"] == "check_in":
                state["checked_in"] = True
            elif e["event_type"] == "check_out":
                state = {"checked_in": False, "on_break": False}
            elif e["event_type"] == "break_start":
                state["on_break"] = True
            elif e["event_type"] == "break_end":
                state["on_break"] = False

        return state

    @classmethod
    def _get_session_events(cls, employee_id: int, dt: date):
        start, end = cls._get_attendance_window(employee_id, dt)
        return AttendanceEventDB.get_events_for_window(employee_id, start, end)

    @classmethod
    def _get_shift_window(cls, shift, dt):
        if not shift:
            return (
                datetime.combine(dt, time.min),
                datetime.combine(dt, time.max),
                8.0,
                False,
                None,
            )

        start, end = shift["start_time"], shift["end_time"]

        if shift.get("is_night_shift") or end <= start:
            return (
                datetime.combine(dt, start),
                datetime.combine(dt + timedelta(days=1), end),
                8.0,
                True,
                shift["shift_id"],
            )

        return (
            datetime.combine(dt, start),
            datetime.combine(dt, end),
            8.0,
            False,
            shift["shift_id"],
        )
