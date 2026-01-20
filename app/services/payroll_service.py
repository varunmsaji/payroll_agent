from datetime import date, timedelta
from typing import Dict, Any, Tuple

from app.database.connection import get_connection
from app.database.salary import SalaryDB
from app.database.payroll import PayrollDB, PayrollPolicyDB


class PayrollService:
    """
    ✅ Production-grade Payroll Engine
    Attendance + Salary + Policy → Final Payroll
    """

    # ============================================================
    # ✅ PUBLIC PAYROLL GENERATOR
    # ============================================================

    @classmethod
    def generate_for_employee(cls, employee_id: int, year: int, month: int) -> Dict[str, Any]:

        first_day, last_day = cls._get_month_range(year, month)

        # ---------------------------------------------------------
        # ✅ 1️⃣ FETCH ACTIVE PAYROLL POLICY
        # ---------------------------------------------------------
        policy = PayrollPolicyDB.get_active_policy()
        if not policy:
            raise ValueError("No active payroll policy found")

        late_grace = int(policy["late_grace_minutes"])
        late_lop_threshold = int(policy["late_lop_threshold_minutes"])

        early_grace = int(policy["early_exit_grace_minutes"])
        early_lop_threshold = int(policy["early_exit_lop_threshold_minutes"])

        overtime_enabled = bool(policy["overtime_enabled"])
        overtime_multiplier = float(policy["overtime_multiplier"])

        holiday_double_pay = bool(policy["holiday_double_pay"])
        weekend_paid_only_if_worked = bool(policy["weekend_paid_only_if_worked"])
        night_shift_allowance = float(policy["night_shift_allowance"])

        # ---------------------------------------------------------
        # ✅ 2️⃣ FETCH SALARY STRUCTURE
        # ---------------------------------------------------------
        salary_row = SalaryDB.get_active_for_date(employee_id, first_day)

        if salary_row:
            basic = float(salary_row["basic"])
            hra = float(salary_row["hra"])
            allowances = float(salary_row.get("allowances", 0) or 0)
            fixed_deductions = float(salary_row.get("deductions", 0) or 0)
        else:
            base_salary = SalaryDB.get_base_salary_from_employee(employee_id)
            if base_salary is None:
                raise ValueError(f"No salary found for employee_id={employee_id}")

            basic = base_salary * 0.5
            hra = base_salary * 0.4
            allowances = base_salary * 0.1
            fixed_deductions = 0.0

        gross_monthly = basic + hra + allowances

        # ---------------------------------------------------------
        # ✅ 3️⃣ FETCH ATTENDANCE SUMMARY
        # ---------------------------------------------------------
        summary = cls._get_attendance_summary(employee_id, first_day, last_day)

        working_days = summary["working_days"]
        paid_days = summary["paid_days"]
        lop_days_from_absent = summary["lop_days_from_absent"]

        total_late_minutes = summary["total_late_minutes"]
        total_early_minutes = summary["total_early_minutes"]
        total_overtime_minutes = summary["total_overtime_minutes"]

        total_net_hours = summary["total_net_hours"]
        holiday_count = summary["holiday_count"]
        night_shift_days = summary["night_shift_days"]

        # ---------------------------------------------------------
        # ✅ 4️⃣ HANDLE ZERO WORKING DAYS
        # ---------------------------------------------------------
        if working_days <= 0:
            payroll_row = PayrollDB.upsert_payroll(
                employee_id=employee_id,
                year=year,
                month=month,

                working_days=0,
                present_days=0,
                total_hours=0,

                gross_salary=gross_monthly,
                net_salary=0,

                basic_pay=basic,
                hra_pay=hra,
                allowances_pay=allowances,

                overtime_hours=0,
                overtime_pay=0,

                lop_days=0,
                lop_deduction=0,

                late_penalty=0,
                early_penalty=0,

                holiday_pay=0,
                night_shift_allowance=0,

                is_finalized=False
            )

            return {"payroll": payroll_row, "reason": "No working days"}

        per_day_salary = gross_monthly / float(working_days)

        # ---------------------------------------------------------
        # ✅ 5️⃣ LATE + EARLY EXIT → LOP
        # ---------------------------------------------------------
        combined_late_early = max(0, total_late_minutes - late_grace) + \
                              max(0, total_early_minutes - early_grace)

        extra_lop_days = 0.5 if combined_late_early >= late_lop_threshold else 0
        total_lop_days = lop_days_from_absent + extra_lop_days
        lop_amount = total_lop_days * per_day_salary

        # ---------------------------------------------------------
        # ✅ 6️⃣ OVERTIME PAY
        # ---------------------------------------------------------
        if overtime_enabled:
            overtime_hours = total_overtime_minutes / 60.0
            hourly_rate = gross_monthly / (working_days * 8.0)
            overtime_pay = overtime_hours * hourly_rate * overtime_multiplier
        else:
            overtime_hours = 0
            overtime_pay = 0.0

        # ---------------------------------------------------------
        # ✅ 7️⃣ HOLIDAY PAY
        # ---------------------------------------------------------
        holiday_pay = holiday_count * per_day_salary if holiday_double_pay else 0.0

        # ---------------------------------------------------------
        # ✅ 8️⃣ NIGHT SHIFT ALLOWANCE
        # ---------------------------------------------------------
        night_shift_bonus = night_shift_days * night_shift_allowance

        # ---------------------------------------------------------
        # ✅ 9️⃣ FINAL NET SALARY
        # ---------------------------------------------------------
        net_salary = (
            gross_monthly
            - fixed_deductions
            - lop_amount
            + overtime_pay
            + holiday_pay
            + night_shift_bonus
        )

        # ---------------------------------------------------------
        # ✅ 🔥 10️⃣ FINAL UPSERT (FULL DB PERSISTENCE FIX)
        # ---------------------------------------------------------
        payroll_row = PayrollDB.upsert_payroll(
            employee_id=employee_id,
            year=year,
            month=month,

            working_days=working_days,
            present_days=paid_days,
            total_hours=total_net_hours,

            gross_salary=gross_monthly,
            net_salary=net_salary,

            basic_pay=basic,
            hra_pay=hra,
            allowances_pay=allowances,

            overtime_hours=overtime_hours,
            overtime_pay=overtime_pay,

            lop_days=total_lop_days,
            lop_deduction=lop_amount,

            late_penalty=float(max(0, total_late_minutes - late_grace)),
            early_penalty=float(max(0, total_early_minutes - early_grace)),

            holiday_pay=holiday_pay,
            night_shift_allowance=night_shift_bonus,

            is_finalized=False
        )

        # ---------------------------------------------------------
        # ✅ 11️⃣ LOCK ATTENDANCE
        # ---------------------------------------------------------
        PayrollDB.lock_attendance_for_period(employee_id, first_day, last_day)

        return {
            "payroll": payroll_row,
            "breakdown": {
                "gross_salary": gross_monthly,
                "basic": basic,
                "hra": hra,
                "allowances": allowances,
                "deductions": fixed_deductions,
                "working_days": working_days,
                "paid_days": paid_days,
                "lop_days": total_lop_days,
                "lop_amount": lop_amount,
                "overtime_minutes": total_overtime_minutes,
                "overtime_pay": overtime_pay,
                "holiday_days": holiday_count,
                "holiday_pay": holiday_pay,
                "night_shift_days": night_shift_days,
                "night_shift_bonus": night_shift_bonus,
                "net_salary": net_salary,
            },
            "policy_snapshot": dict(policy),
        }

    # ============================================================
    # ✅ ATTENDANCE SUMMARY ENGINE
    # ============================================================

    @classmethod
    def _get_attendance_summary(cls, employee_id: int, start_date: date, end_date: date) -> Dict[str, Any]:

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE is_weekend = FALSE) AS working_days,
                COUNT(*) FILTER (
                    WHERE status IN ('present','half_day','short_hours','holiday','on_leave','week_off')
                    AND is_weekend = FALSE
                ) AS paid_days,
                COUNT(*) FILTER (
                    WHERE status = 'absent'
                    AND is_weekend = FALSE
                ) AS lop_days_from_absent,
                COALESCE(SUM(net_hours), 0) AS total_net_hours,
                COALESCE(SUM(late_minutes), 0) AS total_late_minutes,
                COALESCE(SUM(early_exit_minutes), 0) AS total_early_minutes,
                COALESCE(SUM(overtime_minutes), 0) AS total_overtime_minutes,
                COUNT(*) FILTER (WHERE is_holiday = TRUE) AS holiday_count,
                COUNT(*) FILTER (WHERE is_night_shift = TRUE) AS night_shift_days
            FROM attendance
            WHERE employee_id = %s
              AND date BETWEEN %s AND %s;
            """,
            (employee_id, start_date, end_date),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        return {
            "working_days": row[0] or 0,
            "paid_days": row[1] or 0,
            "lop_days_from_absent": row[2] or 0,
            "total_net_hours": float(row[3] or 0),
            "total_late_minutes": int(row[4] or 0),
            "total_early_minutes": int(row[5] or 0),
            "total_overtime_minutes": int(row[6] or 0),
            "holiday_count": int(row[7] or 0),
            "night_shift_days": int(row[8] or 0),
        }

    # ============================================================
    # ✅ DATE UTILITY
    # ============================================================

    @staticmethod
    def _get_month_range(year: int, month: int) -> Tuple[date, date]:

        first_day = date(year, month, 1)

        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        return first_day, last_day
