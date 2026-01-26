"""
SQLAlchemy ORM models for all database tables.

These models represent the database schema and can be used for:
- Auto-generating Alembic migrations
- Type-safe database queries
- ORM operations (optional, can keep using raw SQL)
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    BigInteger,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.base import Base


# ============================================================
# EMPLOYEE TABLES
# ============================================================


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    designation = Column(String)
    department = Column(String)
    date_of_joining = Column(Date)
    base_salary = Column(Numeric, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())
    manager_id = Column(Integer, ForeignKey("employees.employee_id"))

    # Relationships
    manager = relationship("Employee", remote_side=[employee_id], backref="subordinates")
    attendance_records = relationship("Attendance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", foreign_keys="LeaveRequest.employee_id")
    payroll_records = relationship("Payroll", back_populates="employee")


# ============================================================
# SHIFTS
# ============================================================


class Shift(Base):
    __tablename__ = "shifts"

    shift_id = Column(Integer, primary_key=True, autoincrement=True)
    shift_name = Column(String, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_night_shift = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    break_start = Column(Time)
    break_end = Column(Time)
    break_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    break_grace_minutes = Column(Integer, default=0)
    break_required = Column(Boolean, default=True)
    break_violation_action = Column(String, default="short_hours")
    required_hours = Column(Numeric, nullable=False, default=8.0)
    allow_early_overtime = Column(Boolean, default=False)
    early_overtime_grace_minutes = Column(Integer, default=0)
    early_overtime_max_minutes = Column(Integer, default=0)
    early_overtime_requires_approval = Column(Boolean, default=False)
    late_grace_minutes = Column(Integer, nullable=False, default=0)

    # Relationships
    attendance_records = relationship("Attendance", back_populates="shift")
    employee_shifts = relationship("EmployeeShift", back_populates="shift")


class EmployeeShift(Base):
    __tablename__ = "employee_shifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    shift_id = Column(Integer, ForeignKey("shifts.shift_id"))
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    shift = relationship("Shift", back_populates="employee_shifts")


# ============================================================
# ATTENDANCE
# ============================================================


class Attendance(Base):
    __tablename__ = "attendance"

    attendance_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    date = Column(Date, nullable=False)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    total_hours = Column(Numeric)
    status = Column(String, default="present")
    created_at = Column(DateTime, server_default=func.now())
    late_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    break_minutes = Column(Integer, default=0)
    shift_id = Column(Integer, ForeignKey("shifts.shift_id"))
    net_hours = Column(Numeric)
    is_late = Column(Boolean, default=False)
    is_early_checkout = Column(Boolean, default=False)
    early_exit_minutes = Column(Integer, default=0)
    is_overtime = Column(Boolean, default=False)
    is_weekend = Column(Boolean, default=False)
    is_holiday = Column(Boolean, default=False)
    is_night_shift = Column(Boolean, default=False)
    is_payroll_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime)
    override_comment = Column(Text)
    overridden_by = Column(Integer)
    overridden_at = Column(DateTime)
    early_overtime_minutes = Column(Integer, default=0)

    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")
    shift = relationship("Shift", back_populates="attendance_records")


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    event_type = Column(String, nullable=False)
    event_time = Column(DateTime, nullable=False)
    source = Column(String, default="manual")
    meta = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    session_id = Column(BigInteger, ForeignKey("attendance_sessions.session_id"))


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    session_id = Column(BigInteger, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, nullable=False)
    shift_id = Column(Integer)
    session_date = Column(Date, nullable=False)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime)
    total_work_seconds = Column(Integer, default=0)
    total_break_seconds = Column(Integer, default=0)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AttendancePolicy(Base):
    __tablename__ = "attendance_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    late_grace_minutes = Column(Integer, nullable=False)
    early_exit_grace_minutes = Column(Integer, nullable=False)
    full_day_fraction = Column(Numeric, nullable=False)
    half_day_fraction = Column(Numeric, nullable=False)
    night_shift_enabled = Column(Boolean, default=True)
    overtime_enabled = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    early_checkin_grace_minutes = Column(Integer, default=0)
    early_checkin_action = Column(String, default="cap")


# ============================================================
# LEAVE MANAGEMENT
# ============================================================


class LeaveType(Base):
    __tablename__ = "leave_types"

    leave_type_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    yearly_quota = Column(Integer, nullable=False, default=0)
    is_paid = Column(Boolean, default=True)
    carry_forward = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")
    leave_balances = relationship("LeaveBalance", back_populates="leave_type")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    leave_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric, nullable=False)
    reason = Column(Text)
    status = Column(String, default="pending")
    applied_on = Column(DateTime, server_default=func.now())
    approved_by = Column(Integer, ForeignKey("employees.employee_id"))
    approved_on = Column(DateTime)

    # Relationships
    leave_type = relationship("LeaveType", back_populates="leave_requests")


class LeaveBalance(Base):
    __tablename__ = "leave_balance"

    balance_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_quota = Column(Numeric, nullable=False, default=0)
    used = Column(Numeric, nullable=False, default=0)
    remaining = Column(Numeric, nullable=False, default=0)
    carry_forwarded = Column(Numeric, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    leave_type = relationship("LeaveType", back_populates="leave_balances")


class Holiday(Base):
    __tablename__ = "holidays"

    holiday_id = Column(Integer, primary_key=True, autoincrement=True)
    holiday_date = Column(Date, nullable=False)
    name = Column(String, nullable=False)
    is_optional = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================
# PAYROLL
# ============================================================


class Payroll(Base):
    __tablename__ = "payroll"

    payroll_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    working_days = Column(Integer)
    present_days = Column(Integer)
    total_hours = Column(Numeric)
    gross_salary = Column(Numeric)
    net_salary = Column(Numeric)
    generated_at = Column(DateTime, server_default=func.now())
    basic_pay = Column(Numeric)
    hra_pay = Column(Numeric)
    allowances_pay = Column(Numeric)
    overtime_hours = Column(Numeric, default=0)
    overtime_pay = Column(Numeric, default=0)
    late_penalty = Column(Numeric, default=0)
    early_penalty = Column(Numeric, default=0)
    lop_days = Column(Numeric, default=0)
    lop_deduction = Column(Numeric, default=0)
    night_shift_allowance = Column(Numeric, default=0)
    holiday_pay = Column(Numeric, default=0)
    is_finalized = Column(Boolean, default=False)

    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")


class PayrollPolicy(Base):
    __tablename__ = "payroll_policies"

    policy_id = Column(Integer, primary_key=True, autoincrement=True)
    late_grace_minutes = Column(Integer, default=10)
    late_lop_threshold_minutes = Column(Integer, default=180)
    early_exit_grace_minutes = Column(Integer, default=15)
    early_exit_lop_threshold_minutes = Column(Integer, default=60)
    overtime_enabled = Column(Boolean, default=True)
    overtime_multiplier = Column(Numeric, default=1.5)
    holiday_double_pay = Column(Boolean, default=True)
    weekend_paid_only_if_worked = Column(Boolean, default=True)
    night_shift_allowance = Column(Numeric, default=500)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class SalaryStructure(Base):
    __tablename__ = "salary_structure"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    basic = Column(Numeric, nullable=False)
    hra = Column(Numeric, nullable=False)
    allowances = Column(Numeric, default=0)
    deductions = Column(Numeric, default=0)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================
# WORKFLOWS
# ============================================================


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    module = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    steps = relationship("WorkflowStep", back_populates="workflow")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    role = Column(String, nullable=False)
    is_final = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    workflow = relationship("Workflow", back_populates="steps")


# Import all models to ensure they're registered with Base
__all__ = [
    "Base",
    "Employee",
    "Shift",
    "EmployeeShift",
    "Attendance",
    "AttendanceEvent",
    "AttendanceSession",
    "AttendancePolicy",
    "LeaveType",
    "LeaveRequest",
    "LeaveBalance",
    "Holiday",
    "Payroll",
    "PayrollPolicy",
    "SalaryStructure",
    "Workflow",
    "WorkflowStep",
]
