# HRMS Database Schema

## 📊 Database Overview

| Property | Value |
|----------|-------|
| **Database Name** | `hrms_db` |
| **RDBMS** | PostgreSQL |
| **Host** | localhost |
| **Port** | 5432 |
| **Connection Library** | psycopg2 with RealDictCursor |

---

## 📋 Tables Summary (18 Tables)

Your database has **18 tables** organized into 6 modules:

### 1. Employee & Organization
| Table | Description |
|-------|-------------|
| `employees` | Core employee master data (name, email, designation, department, salary, manager hierarchy) |
| `employee_shifts` | Time-bound shift assignments per employee |

### 2. Shift Management
| Table | Description |
|-------|-------------|
| `shifts` | Shift definitions (timing, breaks, night shift flags) |

### 3. Attendance System
| Table | Description |
|-------|-------------|
| `attendance_events` | Raw attendance events (check-in, check-out, breaks) |
| `attendance` | Processed daily attendance with payroll-ready metrics |
| `holidays` | Company holiday calendar |

### 4. Salary & Payroll
| Table | Description |
|-------|-------------|
| `salary_structure` | Employee salary components (basic, HRA, allowances) |
| `payroll` | Monthly payroll records with complete breakdowns |
| `payroll_policies` | Configurable payroll calculation policies |

### 5. Leave Management
| Table | Description |
|-------|-------------|
| `leave_types` | Leave type definitions (Sick, Casual, etc.) |
| `employee_leave_balance` | Employee leave balances by year |
| `leave_requests` | Leave applications |
| `leave_history` | Approved leave history (immutable) |

### 6. Workflow Engine
| Table | Description |
|-------|-------------|
| `workflows` | Workflow definitions by module |
| `workflow_steps` | Workflow approval steps |
| `approval_logs` | Approval action logs |
| `request_status` | Current status of workflow requests |

---

## 📝 Detailed Table Columns

### employees

**Purpose:** Core employee master data table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| employee_id | SERIAL | PRIMARY KEY | Unique employee identifier |
| first_name | VARCHAR(100) | | Employee's first name |
| last_name | VARCHAR(100) | | Employee's last name |
| email | VARCHAR(255) | UNIQUE | Employee email (unique) |
| phone | VARCHAR(20) | | Contact number |
| designation | VARCHAR(100) | | Job title/role |
| department | VARCHAR(100) | | Department name |
| date_of_joining | DATE | | Joining date |
| base_salary | NUMERIC(10,2) | NOT NULL | Base salary amount |
| manager_id | INT | FK → employees | Manager (self-reference) |
| status | VARCHAR(20) | DEFAULT 'active' | active/ex_employee |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Self-referencing hierarchy via `manager_id` for organizational structure
- Soft delete using status field ('active' vs 'ex_employee')
- Circular reference prevention enforced at application layer

---

### shifts

**Purpose:** Define work shift schedules

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| shift_id | SERIAL | PRIMARY KEY | Unique shift identifier |
| shift_name | VARCHAR(100) | NOT NULL | Shift name (e.g., "Morning", "Night") |
| start_time | TIME | NOT NULL | Shift start time |
| end_time | TIME | NOT NULL | Shift end time |
| is_night_shift | BOOLEAN | DEFAULT FALSE | Night shift indicator |
| break_start | TIME | | Break start time |
| break_end | TIME | | Break end time |
| break_minutes | INT | DEFAULT 0 | Total break duration in minutes |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Soft delete using `is_active` flag
- Break management with dedicated fields
- Night shift allowance calculation support

---

### employee_shifts

**Purpose:** Time-bound shift assignments for employees

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique assignment ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| shift_id | INT | FK → shifts (SET NULL) | Shift reference |
| effective_from | DATE | NOT NULL | Assignment start date |
| effective_to | DATE | | Assignment end date (NULL = current) |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Time-bound assignments supporting shift history
- Automatic closure of previous shift when new shift is assigned
- Cascading delete removes assignments when employee is deleted

---

### attendance_events

**Purpose:** Raw attendance event logs (check-in, check-out, breaks)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | SERIAL | PRIMARY KEY | Unique event ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| event_type | VARCHAR(20) | NOT NULL | check_in, check_out, break_start, break_end |
| event_time | TIMESTAMP | NOT NULL | Event timestamp |
| source | VARCHAR(40) | DEFAULT 'manual' | Event source (biometric, manual, etc.) |
| meta | JSONB | | Additional metadata |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Immutable event log preserving raw attendance data
- Flexible metadata using JSONB for extensibility
- Source tracking for audit trails

---

### attendance

**Purpose:** Processed daily attendance records with payroll-ready metrics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| attendance_id | SERIAL | PRIMARY KEY | Unique attendance ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| shift_id | INT | | Assigned shift for the day |
| date | DATE | NOT NULL | Attendance date |
| check_in | TIMESTAMP | | First check-in time |
| check_out | TIMESTAMP | | Last check-out time |
| total_hours | NUMERIC(5,2) | | Total duration (check-out - check-in) |
| net_hours | NUMERIC(5,2) | | Working hours (total - breaks) |
| break_minutes | INT | DEFAULT 0 | Total break duration |
| overtime_minutes | INT | DEFAULT 0 | Overtime worked |
| late_minutes | INT | DEFAULT 0 | Late arrival minutes |
| early_exit_minutes | INT | DEFAULT 0 | Early departure minutes |
| is_late | BOOLEAN | DEFAULT FALSE | Late arrival flag |
| is_early_checkout | BOOLEAN | DEFAULT FALSE | Early exit flag |
| is_overtime | BOOLEAN | DEFAULT FALSE | Overtime worked flag |
| is_weekend | BOOLEAN | DEFAULT FALSE | Weekend work flag |
| is_holiday | BOOLEAN | DEFAULT FALSE | Holiday work flag |
| is_night_shift | BOOLEAN | DEFAULT FALSE | Night shift flag |
| status | VARCHAR(20) | DEFAULT 'present' | present/absent/leave/half_day |
| is_payroll_locked | BOOLEAN | DEFAULT FALSE | Payroll lock flag |
| locked_at | TIMESTAMP | | Lock timestamp |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (employee_id, date)

**Key Features:**
- Comprehensive payroll metrics pre-calculated
- Payroll lock mechanism prevents retroactive changes
- Boolean flags for quick filtering and reporting

---

### holidays

**Purpose:** Company holiday calendar

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| holiday_id | SERIAL | PRIMARY KEY | Unique holiday ID |
| holiday_date | DATE | UNIQUE | Holiday date |
| name | VARCHAR(100) | | Holiday name |
| is_optional | BOOLEAN | DEFAULT FALSE | Optional holiday flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Unique dates prevent duplicate holidays
- Optional holidays for regional/personal holidays

---

### salary_structure

**Purpose:** Time-bound employee salary component definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique structure ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| basic | NUMERIC(10,2) | NOT NULL | Basic salary |
| hra | NUMERIC(10,2) | NOT NULL | House Rent Allowance |
| allowances | NUMERIC(10,2) | DEFAULT 0 | Other allowances |
| deductions | NUMERIC(10,2) | DEFAULT 0 | Standard deductions |
| effective_from | DATE | NOT NULL | Structure start date |
| effective_to | DATE | | Structure end date (NULL = current) |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Time-bound structures supporting salary history
- Component-wise breakdown for detailed payroll
- Fallback to base_salary from employees table if no structure exists

---

### payroll

**Purpose:** Monthly payroll records

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| payroll_id | SERIAL | PRIMARY KEY | Unique payroll ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| month | INT | NOT NULL | Payroll month (1-12) |
| year | INT | NOT NULL | Payroll year |
| working_days | INT | | Total working days in month |
| present_days | INT | | Days present |
| total_hours | NUMERIC(10,2) | | Total hours worked |
| gross_salary | NUMERIC(10,2) | | Gross salary (before deductions) |
| net_salary | NUMERIC(10,2) | | Net salary (take-home) |
| basic_pay | NUMERIC(10,2) | | Basic salary component |
| hra_pay | NUMERIC(10,2) | | HRA component |
| allowances_pay | NUMERIC(10,2) | | Allowances component |
| overtime_hours | NUMERIC(10,2) | | Total overtime hours |
| overtime_pay | NUMERIC(10,2) | | Overtime payment |
| lop_days | NUMERIC(5,2) | | Loss of Pay days |
| lop_deduction | NUMERIC(10,2) | | LOP deduction amount |
| late_penalty | NUMERIC(10,2) | | Late arrival penalty |
| early_penalty | NUMERIC(10,2) | | Early exit penalty |
| holiday_pay | NUMERIC(10,2) | | Holiday work payment |
| night_shift_allowance | NUMERIC(10,2) | | Night shift allowance |
| is_finalized | BOOLEAN | DEFAULT FALSE | Finalization flag |
| generated_at | TIMESTAMP | DEFAULT NOW() | Generation timestamp |

**Unique Constraint:** (employee_id, month, year)

**Key Features:**
- Comprehensive breakdown of all payroll components
- Finalization flag prevents accidental regeneration
- Upsert capability for draft payroll updates

---

### payroll_policies

**Purpose:** Configurable payroll calculation policies

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique policy ID |
| late_grace_minutes | INT | DEFAULT 0 | Grace period for late arrival |
| late_lop_threshold_minutes | INT | | Late minutes triggering LOP |
| early_exit_grace_minutes | INT | DEFAULT 0 | Grace period for early exit |
| early_exit_lop_threshold_minutes | INT | | Early exit minutes for LOP |
| overtime_enabled | BOOLEAN | DEFAULT TRUE | Overtime calculation enabled |
| overtime_multiplier | NUMERIC(3,2) | DEFAULT 1.5 | Overtime pay multiplier |
| holiday_double_pay | BOOLEAN | DEFAULT TRUE | Double pay for holidays |
| weekend_paid_only_if_worked | BOOLEAN | DEFAULT FALSE | Weekend pay policy |
| night_shift_allowance | NUMERIC(10,2) | DEFAULT 0 | Night shift extra pay |
| active | BOOLEAN | DEFAULT TRUE | Active policy flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Single active policy at any time
- Configurable thresholds for penalties and bonuses
- Multiplier-based calculations for overtime

---

### leave_types

**Purpose:** Define available leave types

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| leave_type_id | SERIAL | PRIMARY KEY | Unique leave type ID |
| name | VARCHAR(50) | NOT NULL | Leave type name |
| code | VARCHAR(10) | UNIQUE, NOT NULL | Short code (e.g., "SL", "CL") |
| yearly_quota | INT | NOT NULL, DEFAULT 0 | Default annual quota |
| is_paid | BOOLEAN | DEFAULT TRUE | Paid/unpaid leave flag |
| carry_forward | BOOLEAN | DEFAULT TRUE | Carry forward enabled |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- Unique codes for programmatic access
- Paid/unpaid distinction affects payroll
- Carry forward policy configurable per type

---

### employee_leave_balance

**Purpose:** Annual leave balances per employee

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique balance ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| leave_type_id | INT | FK → leave_types | Leave type reference |
| year | INT | NOT NULL | Balance year |
| total_quota | INT | NOT NULL | Total allocated leaves |
| used | INT | DEFAULT 0 | Leaves consumed |
| remaining | INT | NOT NULL | Leaves remaining |
| carry_forwarded | INT | DEFAULT 0 | Carried from previous year |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (employee_id, leave_type_id, year)

**Key Features:**
- Yearly balances per leave type
- Automatic deduction on leave approval
- Atomic updates with safe decrement logic

---

### leave_requests

**Purpose:** Leave applications and approval tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| leave_id | SERIAL | PRIMARY KEY | Unique request ID |
| employee_id | INT | FK → employees (CASCADE) | Employee reference |
| leave_type_id | INT | FK → leave_types | Leave type reference |
| start_date | DATE | NOT NULL | Leave start date |
| end_date | DATE | NOT NULL | Leave end date |
| total_days | DECIMAL(5,2) | NOT NULL | Leave duration |
| reason | TEXT | | Employee's reason |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/approved/rejected |
| applied_on | TIMESTAMP | DEFAULT NOW() | Application timestamp |
| approved_by | INT | FK → employees | Approver reference |
| approved_on | TIMESTAMP | | Approval timestamp |

**Key Features:**
- Overlap detection prevents conflicting leaves
- Workflow integration for approvals
- Audit trail with approver and timestamps

---

### leave_history

**Purpose:** Immutable record of approved leaves

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique history ID |
| employee_id | INT | FK → employees | Employee reference |
| leave_type_id | INT | FK → leave_types | Leave type reference |
| start_date | DATE | NOT NULL | Leave start date |
| end_date | DATE | NOT NULL | Leave end date |
| total_days | DECIMAL(5,2) | NOT NULL | Leave duration |
| recorded_on | TIMESTAMP | DEFAULT NOW() | Record timestamp |

**Key Features:**
- Immutable log of all approved leaves
- Used for payroll LOP calculations
- Reporting-friendly consolidated view

---

### workflows

**Purpose:** Define approval workflow configurations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique workflow ID |
| name | VARCHAR(100) | NOT NULL | Workflow name |
| module | VARCHAR(50) | NOT NULL | Module (leave, expense, etc.) |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Index:** Only one active workflow per module

**Key Features:**
- Module-based workflows (leave, payroll, etc.)
- Single active workflow per module enforced
- Version control through activation/deactivation

---

### workflow_steps

**Purpose:** Define sequential approval steps in a workflow

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique step ID |
| workflow_id | INT | FK → workflows (CASCADE) | Workflow reference |
| step_order | INT | NOT NULL | Step sequence number |
| role | VARCHAR(50) | NOT NULL | Approver role (manager, HR, finance, director) |
| is_final | BOOLEAN | DEFAULT FALSE | Final step flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (workflow_id, step_order)

**Key Features:**
- Ordered steps with sequential processing
- Role-based assignment auto-resolves approvers
- Final step flag triggers request completion

---

### approval_logs

**Purpose:** Track individual approval actions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique log ID |
| module | VARCHAR(50) | NOT NULL | Module identifier |
| request_id | INT | NOT NULL | Request identifier (leave_id, etc.) |
| workflow_id | INT | FK → workflows | Workflow reference |
| step_order | INT | NOT NULL | Current step number |
| approver_id | INT | NOT NULL | Assigned approver |
| status | VARCHAR(20) | CHECK (pending/approved/rejected) | Approval status |
| acted_at | TIMESTAMP | | Action timestamp |
| remarks | TEXT | | Approver comments |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (module, request_id, step_order)

**Key Features:**
- Complete audit trail of all approvals
- Security check ensures only assigned approver can act
- Timestamp tracking for SLA monitoring

---

### request_status

**Purpose:** Current overall status of workflow requests

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique status ID |
| module | VARCHAR(50) | NOT NULL | Module identifier |
| request_id | INT | NOT NULL | Request identifier |
| status | VARCHAR(20) | CHECK (pending/approved/rejected) | Overall status |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update time |

**Unique Constraint:** (module, request_id)

**Key Features:**
- Quick status lookup without joining logs
- Updated on every step action
- Module-agnostic design

---

## 🔗 Entity Relationship Diagram

```
┌──────────────┐
│  employees   │◄────┐
└──────────────┘     │
       │             │ manager_id (self-reference)
       │ 1:N         │
       │             │
       ▼             │
┌──────────────────┐ │
│ employee_shifts  │─┘
└──────────────────┘
       │
       │ N:1
       ▼
┌──────────────┐
│   shifts     │
└──────────────┘

┌──────────────┐        ┌──────────────────┐
│  employees   │◄───────│ attendance_events│
└──────────────┘   1:N  └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│  attendance  │
└──────────────┘

┌──────────────┐        ┌──────────────────┐
│  employees   │◄───────│ salary_structure │
└──────────────┘   1:N  └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│   payroll    │
└──────────────┘

┌──────────────┐        ┌────────────────────────┐
│ leave_types  │◄───────│ employee_leave_balance │
└──────────────┘   1:N  └────────────────────────┘
                               │
                               │ 1:N
                               ▼
                        ┌──────────────┐
                        │leave_requests│
                        └──────────────┘
                               │
                               │ 1:1
                               ▼
                        ┌──────────────┐
                        │leave_history │
                        └──────────────┘

┌──────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  workflows   │◄───────│ workflow_steps   │◄───────│ approval_logs    │
└──────────────┘   1:N  └──────────────────┘   N:1  └──────────────────┘
                                                             │
                                                             │ 1:1
                                                             ▼
                                                      ┌──────────────────┐
                                                      │ request_status   │
                                                      └──────────────────┘
```

---

## 📁 Database Files Location

| File | Purpose |
|------|---------|
| `app/database/connection.py` | Database connection configuration |
| `app/database/database.py` | Main table creation |
| `app/database/employee_db.py` | Employee CRUD operations |
| `app/database/shifts_db.py` | Shift definitions CRUD |
| `app/database/employee_shift_db.py` | Shift assignments |
| `app/database/attendence.py` | Attendance operations |
| `app/database/salary.py` | Salary structure management |
| `app/database/payroll.py` | Payroll operations |
| `app/database/leave_database.py` | Leave management |
| `app/database/workflow_database.py` | Workflow engine |

---

## 📊 Recommended Indexes

```sql
-- Attendance lookups
CREATE INDEX idx_attendance_emp_date ON attendance(employee_id, date);
CREATE INDEX idx_attendance_locked ON attendance(is_payroll_locked);

-- Event queries
CREATE INDEX idx_events_emp_time ON attendance_events(employee_id, event_time);

-- Payroll queries
CREATE INDEX idx_payroll_emp_period ON payroll(employee_id, year, month);

-- Leave queries
CREATE INDEX idx_leave_balance_emp_year ON employee_leave_balance(employee_id, year);
CREATE INDEX idx_leave_requests_status ON leave_requests(status, applied_on);

-- Workflow queries
CREATE INDEX idx_approval_logs_approver ON approval_logs(approver_id, status);
CREATE INDEX idx_request_status_module ON request_status(module, status);

-- Existing unique index
CREATE UNIQUE INDEX idx_one_active_workflow_per_module 
ON workflows(module) WHERE is_active = TRUE;
```

---

## 🔒 Data Integrity Rules

### Referential Integrity

1. **CASCADE Deletes:**
   - Employee deletion cascades to: shifts, attendance, salary, payroll, leaves
   - Workflow deletion cascades to: workflow_steps

2. **SET NULL on Delete:**
   - Shift deletion sets `shift_id = NULL` in `employee_shifts`

3. **Protected Deletes:**
   - Workflows with approval history cannot be deleted
   - Enforced at application layer

### Business Rules

1. **Attendance:**
   - Cannot update locked attendance records
   - One check-in/check-out pair per day
   - Holiday/weekend flags auto-calculated

2. **Leave:**
   - Balance deduction atomic with approval
   - Cannot approve overlapping leaves
   - Insufficient balance blocks approval

3. **Payroll:**
   - One payroll per employee per month
   - Finalized payroll locks attendance
   - Cannot regenerate finalized payroll

4. **Workflow:**
   - Only assigned approver can act on pending step
   - Steps processed sequentially
   - Final step approval updates module request status

---

**Document Version:** 2.0  
**Last Updated:** January 10, 2026  
**Schema Version:** Production-ready
