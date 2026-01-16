-- Supabase-compatible schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS approval_logs (
    id integer NOT NULL DEFAULT nextval('approval_logs_id_seq'::regclass),
    module character varying NOT NULL,
    request_id integer NOT NULL,
    workflow_id integer NOT NULL,
    step_order integer NOT NULL,
    approver_id integer NOT NULL,
    status character varying,
    acted_at timestamp without time zone,
    remarks text,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
ALTER TABLE approval_logs ADD FOREIGN KEY (workflow_id) REFERENCES workflows (id);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id integer NOT NULL DEFAULT nextval('attendance_attendance_id_seq'::regclass),
    employee_id integer,
    date date NOT NULL,
    check_in timestamp without time zone,
    check_out timestamp without time zone,
    total_hours numeric,
    status character varying DEFAULT 'present'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    late_minutes integer DEFAULT 0,
    overtime_minutes integer DEFAULT 0,
    break_minutes integer DEFAULT 0,
    shift_id integer,
    net_hours numeric,
    is_late boolean DEFAULT false,
    is_early_checkout boolean DEFAULT false,
    early_exit_minutes integer DEFAULT 0,
    is_overtime boolean DEFAULT false,
    is_weekend boolean DEFAULT false,
    is_holiday boolean DEFAULT false,
    is_night_shift boolean DEFAULT false,
    is_payroll_locked boolean DEFAULT false,
    locked_at timestamp without time zone,
    override_comment text,
    overridden_by integer,
    overridden_at timestamp without time zone,
    early_overtime_minutes integer DEFAULT 0,
    PRIMARY KEY (attendance_id)
);
ALTER TABLE attendance ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE attendance ADD FOREIGN KEY (shift_id) REFERENCES shifts (shift_id);

CREATE TABLE IF NOT EXISTS attendance_events (
    event_id integer NOT NULL DEFAULT nextval('attendance_events_event_id_seq'::regclass),
    employee_id integer,
    event_type character varying NOT NULL,
    event_time timestamp without time zone NOT NULL,
    source character varying DEFAULT 'manual'::character varying,
    meta jsonb,
    created_at timestamp without time zone DEFAULT now(),
    session_id bigint,
    PRIMARY KEY (event_id)
);
ALTER TABLE attendance_events ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE attendance_events ADD FOREIGN KEY (session_id) REFERENCES attendance_sessions (session_id);

CREATE TABLE IF NOT EXISTS attendance_policies (
    id integer NOT NULL DEFAULT nextval('attendance_policies_id_seq'::regclass),
    late_grace_minutes integer NOT NULL,
    early_exit_grace_minutes integer NOT NULL,
    full_day_fraction double precision NOT NULL,
    half_day_fraction double precision NOT NULL,
    night_shift_enabled boolean DEFAULT true,
    overtime_enabled boolean DEFAULT true,
    active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    early_checkin_grace_minutes integer DEFAULT 0,
    early_checkin_action character varying DEFAULT 'cap'::character varying,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS attendance_sessions (
    session_id bigint NOT NULL DEFAULT nextval('attendance_sessions_session_id_seq'::regclass),
    employee_id integer NOT NULL,
    shift_id integer,
    session_date date NOT NULL,
    check_in timestamp without time zone NOT NULL,
    check_out timestamp without time zone,
    total_work_seconds integer DEFAULT 0,
    total_break_seconds integer DEFAULT 0,
    is_closed boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (session_id)
);

CREATE TABLE IF NOT EXISTS bank_details (
    id character varying NOT NULL,
    candidate_id character varying,
    account_holder_name character varying,
    bank_name character varying,
    account_number character varying,
    ifsc_code character varying,
    bank_proof_file_url text,
    extracted_data json,
    verification_status character varying,
    created_at timestamp without time zone,
    PRIMARY KEY (id)
);
ALTER TABLE bank_details ADD FOREIGN KEY (candidate_id) REFERENCES candidates (id);

CREATE TABLE IF NOT EXISTS candidates (
    id character varying NOT NULL,
    full_name character varying,
    email character varying,
    phone character varying,
    dob date,
    gender character varying,
    address text,
    city character varying,
    state character varying,
    country character varying,
    pincode character varying,
    onboarding_status character varying,
    onboarding_source character varying,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS employee_leave_balance (
    id integer NOT NULL DEFAULT nextval('employee_leave_balance_id_seq'::regclass),
    employee_id integer NOT NULL,
    leave_type_id integer NOT NULL,
    year integer NOT NULL,
    total_quota integer NOT NULL,
    used integer DEFAULT 0,
    remaining integer NOT NULL,
    carry_forwarded integer DEFAULT 0,
    PRIMARY KEY (id)
);
ALTER TABLE employee_leave_balance ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE employee_leave_balance ADD FOREIGN KEY (leave_type_id) REFERENCES leave_types (leave_type_id);

CREATE TABLE IF NOT EXISTS employee_shifts (
    id integer NOT NULL DEFAULT nextval('employee_shifts_id_seq'::regclass),
    employee_id integer,
    shift_id integer,
    effective_from date NOT NULL,
    effective_to date,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
ALTER TABLE employee_shifts ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE employee_shifts ADD FOREIGN KEY (shift_id) REFERENCES shifts (shift_id);

CREATE TABLE IF NOT EXISTS employees (
    employee_id integer NOT NULL DEFAULT nextval('employees_employee_id_seq'::regclass),
    first_name character varying,
    last_name character varying,
    email character varying,
    phone character varying,
    designation character varying,
    department character varying,
    date_of_joining date,
    base_salary numeric NOT NULL,
    status character varying DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    manager_id integer,
    PRIMARY KEY (employee_id)
);
ALTER TABLE employees ADD FOREIGN KEY (manager_id) REFERENCES employees (employee_id);

CREATE TABLE IF NOT EXISTS holidays (
    holiday_id integer NOT NULL DEFAULT nextval('holidays_holiday_id_seq'::regclass),
    holiday_date date NOT NULL,
    name character varying NOT NULL,
    is_optional boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (holiday_id)
);

CREATE TABLE IF NOT EXISTS leave_balance (
    balance_id integer NOT NULL DEFAULT nextval('leave_balance_balance_id_seq'::regclass),
    employee_id integer NOT NULL,
    leave_type_id integer NOT NULL,
    year integer NOT NULL,
    total_quota double precision NOT NULL DEFAULT 0,
    used double precision NOT NULL DEFAULT 0,
    remaining double precision NOT NULL DEFAULT 0,
    carry_forwarded double precision NOT NULL DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (balance_id)
);
ALTER TABLE leave_balance ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE leave_balance ADD FOREIGN KEY (leave_type_id) REFERENCES leave_types (leave_type_id);

CREATE TABLE IF NOT EXISTS leave_history (
    id integer NOT NULL DEFAULT nextval('leave_history_id_seq'::regclass),
    employee_id integer NOT NULL,
    leave_type_id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    total_days numeric NOT NULL,
    recorded_on timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
ALTER TABLE leave_history ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE leave_history ADD FOREIGN KEY (leave_type_id) REFERENCES leave_types (leave_type_id);

CREATE TABLE IF NOT EXISTS leave_requests (
    leave_id integer NOT NULL DEFAULT nextval('leave_requests_leave_id_seq'::regclass),
    employee_id integer NOT NULL,
    leave_type_id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    total_days numeric NOT NULL,
    reason text,
    status character varying DEFAULT 'pending'::character varying,
    applied_on timestamp without time zone DEFAULT now(),
    approved_by integer,
    approved_on timestamp without time zone,
    PRIMARY KEY (leave_id)
);
ALTER TABLE leave_requests ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);
ALTER TABLE leave_requests ADD FOREIGN KEY (leave_type_id) REFERENCES leave_types (leave_type_id);
ALTER TABLE leave_requests ADD FOREIGN KEY (approved_by) REFERENCES employees (employee_id);

CREATE TABLE IF NOT EXISTS leave_types (
    leave_type_id integer NOT NULL DEFAULT nextval('leave_types_leave_type_id_seq'::regclass),
    name character varying NOT NULL,
    code character varying NOT NULL,
    yearly_quota integer NOT NULL DEFAULT 0,
    is_paid boolean DEFAULT true,
    carry_forward boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (leave_type_id)
);

CREATE TABLE IF NOT EXISTS payroll (
    payroll_id integer NOT NULL DEFAULT nextval('payroll_payroll_id_seq'::regclass),
    employee_id integer,
    month integer NOT NULL,
    year integer NOT NULL,
    working_days integer,
    present_days integer,
    total_hours numeric,
    gross_salary numeric,
    net_salary numeric,
    generated_at timestamp without time zone DEFAULT now(),
    basic_pay numeric,
    hra_pay numeric,
    allowances_pay numeric,
    overtime_hours numeric DEFAULT 0,
    overtime_pay numeric DEFAULT 0,
    late_penalty numeric DEFAULT 0,
    early_penalty numeric DEFAULT 0,
    lop_days numeric DEFAULT 0,
    lop_deduction numeric DEFAULT 0,
    night_shift_allowance numeric DEFAULT 0,
    holiday_pay numeric DEFAULT 0,
    is_finalized boolean DEFAULT false,
    PRIMARY KEY (payroll_id)
);
ALTER TABLE payroll ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);

CREATE TABLE IF NOT EXISTS payroll_lock (
    id integer NOT NULL DEFAULT nextval('payroll_lock_id_seq'::regclass),
    year integer NOT NULL,
    month integer NOT NULL,
    is_locked boolean NOT NULL DEFAULT false,
    locked_at timestamp without time zone,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS payroll_policies (
    policy_id integer NOT NULL DEFAULT nextval('payroll_policies_policy_id_seq'::regclass),
    late_grace_minutes integer DEFAULT 10,
    late_lop_threshold_minutes integer DEFAULT 180,
    early_exit_grace_minutes integer DEFAULT 15,
    early_exit_lop_threshold_minutes integer DEFAULT 60,
    overtime_enabled boolean DEFAULT true,
    overtime_multiplier numeric DEFAULT 1.5,
    holiday_double_pay boolean DEFAULT true,
    weekend_paid_only_if_worked boolean DEFAULT true,
    night_shift_allowance numeric DEFAULT 500,
    active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (policy_id)
);

CREATE TABLE IF NOT EXISTS request_status (
    id integer NOT NULL DEFAULT nextval('request_status_id_seq'::regclass),
    module character varying NOT NULL,
    request_id integer NOT NULL,
    status character varying,
    updated_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS salary_structure (
    id integer NOT NULL DEFAULT nextval('salary_structure_id_seq'::regclass),
    employee_id integer,
    basic numeric NOT NULL,
    hra numeric NOT NULL,
    allowances numeric DEFAULT 0,
    deductions numeric DEFAULT 0,
    effective_from date NOT NULL,
    effective_to date,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
ALTER TABLE salary_structure ADD FOREIGN KEY (employee_id) REFERENCES employees (employee_id);

CREATE TABLE IF NOT EXISTS shifts (
    shift_id integer NOT NULL DEFAULT nextval('shifts_shift_id_seq'::regclass),
    shift_name character varying NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    is_night_shift boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    break_start time without time zone,
    break_end time without time zone,
    break_minutes integer DEFAULT 0,
    is_active boolean DEFAULT true,
    break_grace_minutes integer DEFAULT 0,
    break_required boolean DEFAULT true,
    break_violation_action character varying DEFAULT 'short_hours'::character varying,
    required_hours numeric NOT NULL DEFAULT 8.0,
    allow_early_overtime boolean DEFAULT false,
    early_overtime_grace_minutes integer DEFAULT 0,
    early_overtime_max_minutes integer DEFAULT 0,
    early_overtime_requires_approval boolean DEFAULT false,
    late_grace_minutes integer NOT NULL DEFAULT 0,
    PRIMARY KEY (shift_id)
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id integer NOT NULL DEFAULT nextval('workflow_steps_id_seq'::regclass),
    workflow_id integer NOT NULL,
    step_order integer NOT NULL,
    role character varying NOT NULL,
    is_final boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
ALTER TABLE workflow_steps ADD FOREIGN KEY (workflow_id) REFERENCES workflows (id);

CREATE TABLE IF NOT EXISTS workflows (
    id integer NOT NULL DEFAULT nextval('workflows_id_seq'::regclass),
    name character varying NOT NULL,
    module character varying NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    PRIMARY KEY (id)
);
