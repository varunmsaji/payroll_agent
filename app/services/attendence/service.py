# app/services/attendence/service.py

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.database.attendence import AttendanceDB, AttendanceEventDB, HolidayDB, ShiftDB
from app.services.attendence.engine import AttendanceEngine
from app.services.attendence.exceptions import AttendanceLocked, AttendanceRejected
from app.services.attendence.policy import AttendancePolicyDB

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


class AttendanceService:

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

        # ✅ Normalize to UTC
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
        if shift:
            shift_start_local = datetime.combine(dt_local, shift["start_time"])
            shift_start = shift_start_local.replace(tzinfo=IST).astimezone(UTC)

            shift_end_local = datetime.combine(dt_local, shift["end_time"])
            shift_end = shift_end_local.replace(tzinfo=IST).astimezone(UTC)

            if shift_end <= shift_start:
                shift_end += timedelta(days=1)

            late_grace = int(shift.get("late_grace_minutes", 0))
            latest_allowed = shift_start + timedelta(minutes=late_grace)

            if not state["checked_in"] and event_time > latest_allowed:
                raise AttendanceRejected(
                    f"Late check-in not allowed after "
                    f"{latest_allowed.astimezone(IST).strftime('%H:%M')}"
                )

        # -------------------------------------------------
        # STATE MACHINE
        # -------------------------------------------------
        had_break = any(e["event_type"] == "break_start" for e in events)

        if not state["checked_in"]:
            action = "check_in"
        elif state["on_break"]:
            action = "break_end"
        elif shift and shift.get("break_required") and not had_break:
            action = "break_start"
        else:
            action = "check_out"

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

    @classmethod
    def _get_session_events(cls, employee_id: int, dt: date):
        shift = ShiftDB.get_employee_shift(employee_id, dt)
        start_local, end_local, *_ = cls._get_shift_window(shift, dt)

        start = start_local.replace(tzinfo=IST).astimezone(UTC) - timedelta(hours=12)
        end = end_local.replace(tzinfo=IST).astimezone(UTC) + timedelta(hours=12)

        return AttendanceEventDB.get_events_for_window(employee_id, start, end)

    @staticmethod
    def _derive_state(events):
        state = {"checked_in": False, "on_break": False}

        for e in events:
            if e["event_type"] == "check_in":
                state["checked_in"] = True
            elif e["event_type"] == "check_out":
                state["checked_in"] = False
                state["on_break"] = False
            elif e["event_type"] == "break_start":
                state["on_break"] = True
            elif e["event_type"] == "break_end":
                state["on_break"] = False

        return state

    @classmethod
    def recalculate_for_date(cls, employee_id: int, dt: date):
        policy = AttendancePolicyDB.get_policy_for_date(dt)
        engine = AttendanceEngine(policy)

        # -------------------------------------------------
        # LOAD SHIFT
        # -------------------------------------------------
        shift = ShiftDB.get_employee_shift(employee_id, dt)

        ws_local, we_local, required_hours, is_night, shift_id = cls._get_shift_window(shift, dt)

        # -------------------------------------------------
        # SHIFT WINDOW → UTC (🔥 CRITICAL)
        # -------------------------------------------------
        ws = ws_local.replace(tzinfo=IST).astimezone(UTC)
        we = we_local.replace(tzinfo=IST).astimezone(UTC)

        # -------------------------------------------------
        # FETCH EVENTS (SAFE WINDOW)
        # -------------------------------------------------
        events = AttendanceEventDB.get_events_for_window(
            employee_id,
            ws,
            we + timedelta(hours=12),
        )

        # -------------------------------------------------
        # ENGINE CALCULATIONS
        # -------------------------------------------------
        work_sec, break_sec, check_in, check_out = engine.compute_work_and_breaks(events)

        # 🔥 REQUIRED FIXES
        total_hours = round((work_sec + break_sec) / 3600, 2)
        net_hours = round(work_sec / 3600, 2)

        late_minutes, is_late = engine.compute_late(shift, dt, check_in)
        early_minutes, is_early_checkout = engine.compute_early(shift, dt, check_out)

        # ✅ OVERTIME (FIXED & STORED)
        overtime_minutes, is_overtime = engine.compute_overtime(
            actual_out=check_out,
            shift_end=we,
            late_minutes=late_minutes,
        )

        status = engine.decide_status(net_hours, required_hours)

        # -------------------------------------------------
        # UPSERT ATTENDANCE (PAYROLL SAFE)
        # -------------------------------------------------
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
