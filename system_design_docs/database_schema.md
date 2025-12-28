# HRMS Database Schema Documentation

## Table of Contents
1. [Overview](#overview)
2. [Database Configuration](#database-configuration)
3. [Core Tables](#core-tables)
4. [Entity Relationship Diagram](#entity-relationship-diagram)
5. [Table Details](#table-details)
6. [Database Access Layer](#database-access-layer)

---

## Overview

This document provides a comprehensive overview of the HRMS (Human Resource Management System) database schema. The system is built on **PostgreSQL** and manages the following core modules:

- **Employee Management** - Employee records, hierarchy, and status tracking
- **Shift Management** - Work shift definitions and assignments
- **Attendance Tracking** - Raw events and processed daily attendance
- **Salary & Payroll** - Salary structures and payroll processing
- **Leave Management** - Leave types, balances, requests, and approval
- **Workflow Engine** - Multi-level approval workflows
- **Holiday Management** - Company holiday calendar

---

## Database Configuration

**Database Name:** `hrms_db`  
**RDBMS:** PostgreSQL  
**Default Port:** 5432  
**Connection Library:** psycopg2 with RealDictCursor for dict-based results

**Configuration Location:** `app/database/connection.py`

```python
DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}
```

---

## Core Tables

The system consists of **18 tables** organized into the following groups:

### 1. Employee & Organization
- `employees` - Core employee information
- `employee_shifts` - Employee shift assignments (time-bound)

### 2. Shift Management
- `shifts` - Shift definitions (timing, breaks, night shift flags)

### 3. Attendance System
- `attendance_events` - Raw attendance events (check-in, check-out, breaks)
- `attendance` - Processed daily attendance records
- `holidays` - Company holiday calendar

### 4. Salary & Payroll
- `salary_structure` - Employee salary components (time-bound)
- `payroll` - Monthly payroll records
- `payroll_policies` - Payroll calculation policies (LOP, overtime, penalties)

### 5. Leave Management
- `leave_types` - Leave type definitions (Sick, Casual, etc.)
- `employee_leave_balance` - Employee leave balances by year
- `leave_requests` - Leave applications
- `leave_history` - Approved leave history

### 6. Workflow Engine
- `workflows` - Workflow definitions by module
- `workflow_steps` - Workflow approval steps
- `approval_logs` - Approval action logs
- `request_status` - Current status of workflow requests

---

## Entity Relationship Diagram

```
┌──────────────┐
│  employees   │◄────┐
└──────────────┘     │
       │             │
       │ 1:N         │ manager_id (self-reference)
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

## Table Details

### 1. employees

**Purpose:** Core employee master data table

**Columns:**

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
| manager_id | INT | REFERENCES employees(employee_id) | Manager (self-reference) |
| status | VARCHAR(20) | DEFAULT 'active' | active/ex_employee |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- **Self-referencing hierarchy** via `manager_id` for organizational structure
- **Soft delete** using status field ('active' vs 'ex_employee')
- **Circular reference prevention** enforced at application layer

**Business Logic:**
- Employees cannot be their own manager
- Prevents circular manager chain assignments
- Designation-based role identification (HR, finance, director, manager)

---

### 2. shifts

**Purpose:** Define work shift schedules

**Columns:**

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
- **Soft delete** using `is_active` flag
- **Break management** with dedicated fields
- **Night shift allowance** calculation support

**Business Logic:**
- Prevents duplicate shift names
- Only active shifts can be assigned

---

### 3. employee_shifts

**Purpose:** Time-bound shift assignments for employees

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique assignment ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
| shift_id | INT | REFERENCES shifts(shift_id) ON DELETE SET NULL | Shift reference |
| effective_from | DATE | NOT NULL | Assignment start date |
| effective_to | DATE | | Assignment end date (NULL = current) |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- **Time-bound assignments** supporting shift history
- **Automatic closure** of previous shift when new shift is assigned
- **Cascading delete** removes assignments when employee is deleted

**Business Logic:**
- Only one active shift per employee (effective_to IS NULL)
- Previous shifts auto-closed when new shift assigned
- Supports shift change history/audit trail

---

### 4. attendance_events

**Purpose:** Raw attendance event logs (check-in, check-out, breaks)

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | SERIAL | PRIMARY KEY | Unique event ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
| event_type | VARCHAR(20) | NOT NULL | check_in, check_out, break_start, break_end |
| event_time | TIMESTAMP | NOT NULL | Event timestamp |
| source | VARCHAR(40) | DEFAULT 'manual' | Event source (biometric, manual, etc.) |
| meta | JSONB | | Additional metadata |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- **Immutable event log** preserving raw attendance data
- **Flexible metadata** using JSONB for extensibility
- **Source tracking** for audit trails

**Business Logic:**
- Events are never updated, only inserted
- Used as source of truth for attendance processing
- Supports multiple check-ins/check-outs per day

---

### 5. attendance

**Purpose:** Processed daily attendance records with payroll-ready metrics

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| attendance_id | SERIAL | PRIMARY KEY | Unique attendance ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
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
- **Comprehensive payroll metrics** pre-calculated
- **Payroll lock mechanism** prevents retroactive changes
- **Boolean flags** for quick filtering and reporting

**Business Logic:**
- One record per employee per day
- Locked records cannot be updated (payroll integrity)
- All time-based calculations stored for audit trails

---

### 6. holidays

**Purpose:** Company holiday calendar

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| holiday_id | SERIAL | PRIMARY KEY | Unique holiday ID |
| holiday_date | DATE | UNIQUE | Holiday date |
| name | VARCHAR(100) | | Holiday name |
| is_optional | BOOLEAN | DEFAULT FALSE | Optional holiday flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- **Unique dates** prevent duplicate holidays
- **Optional holidays** for regional/personal holidays

**Business Logic:**
- Used in attendance processing
- Affects payroll calculation (holiday pay)

---

### 7. salary_structure

**Purpose:** Time-bound employee salary component definitions

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique structure ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
| basic | NUMERIC(10,2) | NOT NULL | Basic salary |
| hra | NUMERIC(10,2) | NOT NULL | House Rent Allowance |
| allowances | NUMERIC(10,2) | DEFAULT 0 | Other allowances |
| deductions | NUMERIC(10,2) | DEFAULT 0 | Standard deductions |
| effective_from | DATE | NOT NULL | Structure start date |
| effective_to | DATE | | Structure end date (NULL = current) |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Key Features:**
- **Time-bound structures** supporting salary history
- **Component-wise breakdown** for detailed payroll
- **Fallback to base_salary** from employees table if no structure exists

**Business Logic:**
- Only one active structure per employee (effective_to IS NULL)
- Historical salary data preserved
- Used for prorated salary calculations

---

### 8. payroll

**Purpose:** Monthly payroll records

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| payroll_id | SERIAL | PRIMARY KEY | Unique payroll ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
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
- **Comprehensive breakdown** of all payroll components
- **Finalization flag** prevents accidental regeneration
- **Upsert capability** for draft payroll updates

**Business Logic:**
- One payroll record per employee per month
- Can be regenerated until finalized
- Locks corresponding attendance records

---

### 9. payroll_policies

**Purpose:** Configurable payroll calculation policies

**Columns:**

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
- **Single active policy** at any time
- **Configurable thresholds** for penalties and bonuses
- **Multiplier-based calculations** for overtime

**Business Logic:**
- Only one policy can be active
- Used by payroll service for all calculations
- Changes tracked through versioning (new records)

---

### 10. leave_types

**Purpose:** Define available leave types

**Columns:**

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
- **Unique codes** for programmatic access
- **Paid/unpaid distinction** affects payroll
- **Carry forward policy** configurable per type

**Business Logic:**
- Used as template for employee leave balances
- Unpaid leaves contribute to LOP calculation

---

### 11. employee_leave_balance

**Purpose:** Annual leave balances per employee

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique balance ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
| leave_type_id | INT | REFERENCES leave_types(leave_type_id) | Leave type reference |
| year | INT | NOT NULL | Balance year |
| total_quota | INT | NOT NULL | Total allocated leaves |
| used | INT | DEFAULT 0 | Leaves consumed |
| remaining | INT | NOT NULL | Leaves remaining |
| carry_forwarded | INT | DEFAULT 0 | Carried from previous year |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (employee_id, leave_type_id, year)

**Key Features:**
- **Yearly balances** per leave type
- **Automatic deduction** on leave approval
- **Atomic updates** with safe decrement logic

**Business Logic:**
- Balance must be sufficient before approval
- Cannot go negative (enforced via WHERE clause)
- Carry forward applied at year start

---

### 12. leave_requests

**Purpose:** Leave applications and approval tracking

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| leave_id | SERIAL | PRIMARY KEY | Unique request ID |
| employee_id | INT | REFERENCES employees(employee_id) ON DELETE CASCADE | Employee reference |
| leave_type_id | INT | REFERENCES leave_types(leave_type_id) | Leave type reference |
| start_date | DATE | NOT NULL | Leave start date |
| end_date | DATE | NOT NULL | Leave end date |
| total_days | DECIMAL(5,2) | NOT NULL | Leave duration |
| reason | TEXT | | Employee's reason |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/approved/rejected |
| applied_on | TIMESTAMP | DEFAULT NOW() | Application timestamp |
| approved_by | INT | REFERENCES employees(employee_id) | Approver reference |
| approved_on | TIMESTAMP | | Approval timestamp |

**Key Features:**
- **Overlap detection** prevents conflicting leaves
- **Workflow integration** for approvals
- **Audit trail** with approver and timestamps

**Business Logic:**
- Validated against leave balance before approval
- Cannot overlap with existing approved leaves
- Balance deducted only after approval

---

### 13. leave_history

**Purpose:** Immutable record of approved leaves

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique history ID |
| employee_id | INT | REFERENCES employees(employee_id) | Employee reference |
| leave_type_id | INT | REFERENCES leave_types(leave_type_id) | Leave type reference |
| start_date | DATE | NOT NULL | Leave start date |
| end_date | DATE | NOT NULL | Leave end date |
| total_days | DECIMAL(5,2) | NOT NULL | Leave duration |
| recorded_on | TIMESTAMP | DEFAULT NOW() | Record timestamp |

**Key Features:**
- **Immutable log** of all approved leaves
- **Used for payroll** LOP calculations
- **Reporting-friendly** consolidated view

**Business Logic:**
- Auto-populated on leave approval
- Used to calculate unpaid leave days for payroll
- Never updated or deleted

---

### 14. workflows

**Purpose:** Define approval workflow configurations

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique workflow ID |
| name | VARCHAR(100) | NOT NULL | Workflow name |
| module | VARCHAR(50) | NOT NULL | Module (leave, expense, etc.) |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Index:** Only one active workflow per module

**Key Features:**
- **Module-based workflows** (leave, payroll, etc.)
- **Single active workflow** per module enforced
- **Version control** through activation/deactivation

**Business Logic:**
- New workflows start inactive
- Activating a workflow deactivates others for same module
- Cannot delete workflows with approval history

---

### 15. workflow_steps

**Purpose:** Define sequential approval steps in a workflow

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique step ID |
| workflow_id | INT | REFERENCES workflows(id) ON DELETE CASCADE | Workflow reference |
| step_order | INT | NOT NULL | Step sequence number |
| role | VARCHAR(50) | NOT NULL | Approver role (manager, HR, finance, director) |
| is_final | BOOLEAN | DEFAULT FALSE | Final step flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (workflow_id, step_order)

**Key Features:**
- **Ordered steps** with sequential processing
- **Role-based assignment** auto-resolves approvers
- **Final step flag** triggers request completion

**Business Logic:**
- Steps processed in order
- Roles resolved to employees dynamically
- Manager role uses employee's manager_id

---

### 16. approval_logs

**Purpose:** Track individual approval actions

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique log ID |
| module | VARCHAR(50) | NOT NULL | Module identifier |
| request_id | INT | NOT NULL | Request identifier (leave_id, etc.) |
| workflow_id | INT | REFERENCES workflows(id) | Workflow reference |
| step_order | INT | NOT NULL | Current step number |
| approver_id | INT | NOT NULL | Assigned approver |
| status | VARCHAR(20) | CHECK (pending/approved/rejected) | Approval status |
| acted_at | TIMESTAMP | | Action timestamp |
| remarks | TEXT | | Approver comments |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Unique Constraint:** (module, request_id, step_order)

**Key Features:**
- **Complete audit trail** of all approvals
- **Security check** ensures only assigned approver can act
- **Timestamp tracking** for SLA monitoring

**Business Logic:**
- One pending step at a time per request
- Approver verification before allowing action
- Creates next step on approval (if not final)

---

### 17. request_status

**Purpose:** Current overall status of workflow requests

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique status ID |
| module | VARCHAR(50) | NOT NULL | Module identifier |
| request_id | INT | NOT NULL | Request identifier |
| status | VARCHAR(20) | CHECK (pending/approved/rejected) | Overall status |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update time |

**Unique Constraint:** (module, request_id)

**Key Features:**
- **Quick status lookup** without joining logs
- **Updated on every step** action
- **Module-agnostic** design

**Business Logic:**
- Updated when workflow starts, approves, or rejects
- Final status reflects workflow outcome
- Used for inbox/dashboard queries

---

## Database Access Layer

The application uses a **Data Access Object (DAO)** pattern with dedicated database classes:

### Connection Management
- **File:** `app/database/connection.py`
- **Function:** `get_connection()` - Returns psycopg2 connection
- **Cursor Type:** RealDictCursor (returns rows as dictionaries)

### Database Classes

| File | Class | Purpose |
|------|-------|---------|
| `employee_db.py` | EmployeeDB | Employee CRUD, manager queries, status management |
| `shifts_db.py` | ShiftDB | Shift definitions CRUD |
| `employee_shift_db.py` | EmployeeShiftDB | Shift assignments, history tracking |
| `attendence.py` | AttendanceEventDB | Raw event logging |
| `attendence.py` | AttendanceDB | Processed attendance CRUD |
| `attendence.py` | HolidayDB | Holiday management |
| `salary.py` | SalaryDB | Salary structure management |
| `payroll.py` | PayrollDB | Payroll CRUD, attendance locking |
| `payroll.py` | PayrollPolicyDB | Policy configuration |
| `leave_database.py` | LeaveTypeDB | Leave type definitions |
| `leave_database.py` | LeaveBalanceDB | Balance management |
| `leave_database.py` | LeaveRequestDB | Leave application workflow |
| `leave_database.py` | LeaveHistoryDB | Leave history, LOP calculations |
| `workflow_database.py` | WorkflowDB (functions) | Workflow engine operations |

### Transaction Management

**Critical Transactional Operations:**

1. **Leave Approval** (`LeaveRequestDB.approve_leave_transaction`)
   - Updates leave request status
   - Deducts leave balance (if paid)
   - Inserts into leave history
   - **Fully atomic** with rollback on failure

2. **Shift Assignment** (`EmployeeShiftDB.assign_shift`)
   - Closes previous active shift
   - Creates new shift assignment
   - **Single transaction** ensuring consistency

3. **Attendance Upsert** (`AttendanceDB.upsert_full_attendance`)
   - Updates or inserts attendance
   - **Respects payroll lock** (locked records not updated)
   - **ON CONFLICT** handling for idempotency

4. **Payroll Generation** (`PayrollDB.upsert_payroll`)
   - Creates or updates payroll record
   - Locks attendance records for the period
   - **Prevents retroactive changes**

### Safety Features

1. **Circular Reference Prevention**
   - Manager assignment validates against circular chains
   - Application-level validation in `EmployeeDB.set_manager`

2. **Soft Deletes**
   - Employees: `status = 'ex_employee'`
   - Shifts: `is_active = FALSE`
   - Preserves historical data integrity

3. **Unique Constraints**
   - One attendance record per employee per day
   - One payroll record per employee per month/year
   - One active workflow per module
   - One leave balance per employee/type/year

4. **Payroll Lock Mechanism**
   - Attendance locked after payroll generation
   - Updates blocked on locked records
   - Ensures audit compliance

5. **Role-Based Approver Resolution**
   - Dynamic approver assignment based on organizational hierarchy
   - Supports: manager, HR, finance, director roles

---

## Data Integrity Rules

### Referential Integrity

1. **CASCADE Deletes:**
   - Employee deletion cascades to: shifts, attendance, salary, payroll, leaves
   - Workflow deletion cascades to: workflow_steps

2. **SET NULL on Delete:**
   - Shift deletion sets `shift_id = NULL` in `employee_shifts`

3. **Protected Deletes:**
   - Workflows with approval history cannot be deleted
   - Enforced at application layer

### Business Rules Enforcement

1. **Attendance:**
   - Cannot update locked attendance records
   - One check-in/check-out pair per day (via processing logic)
   - Holiday/weekend flags auto-calculated

2. **Leave:**
   - Balance deduction atomic with approval
   - Cannot approve overlapping leaves
   - Insufficient balance blocks approval

3. **Payroll:**
   - One payroll per employee per month
   - Finalized payroll locks attendance
   - Cannot regenerate finalized payroll (application check)

4. **Workflow:**
   - Only assigned approver can act on pending step
   - Steps processed sequentially
   - Final step approval updates module request status

---

## Indexes and Performance

### Recommended Indexes

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

## Migration Strategy

Currently, the system uses **direct DDL execution** via `database.py` and individual module files.

### Current Schema Creation
- **Main tables:** `database.py::create_tables()`
- **Leave tables:** `leave_database.py::LeaveTables.create_tables()`
- **Workflow tables:** `workflow_database.py::create_workflow_tables()`

### Recommended Migration to Alembic

For production environments, consider migrating to Alembic for:
- Version-controlled schema changes
- Safe production deployments
- Rollback capabilities
- Team collaboration

---

## Security Considerations

1. **SQL Injection Prevention:**
   - All queries use parameterized statements
   - No string concatenation in SQL

2. **Password Storage:**
   - Currently stored in plain text in connection.py
   - **RECOMMENDATION:** Move to environment variables

3. **Audit Trails:**
   - All approval actions logged with timestamps
   - Leave history immutable
   - Payroll changes tracked via locked attendance

4. **Access Control:**
   - Workflow approvals verify approver identity
   - Manager assignments validated against loops
   - Status checks prevent unauthorized operations

---

## Known Limitations & Technical Debt

1. **Database Credentials:**
   - Hardcoded in multiple files (connection.py, attendence.py, leave_database.py, workflow_database.py)
   - **RECOMMENDATION:** Centralize in environment variables

2. **Schema Synchronization:**
   - Extended attendance schema defined in code but may not match database.py
   - **Fields in code but not in database.py:** shift_id, net_hours, break_minutes, overtime_minutes, late_minutes, early_exit_minutes, boolean flags, payroll lock fields

3. **Shift Schema Mismatch:**
   - shifts_db.py uses break_start, break_end, break_minutes, is_active
   - database.py only has basic shift fields
   - **RECOMMENDATION:** Update database.py to match extended schema

4. **No Alembic Migrations:**
   - Schema changes done manually
   - No version control for database changes

5. **Manager Assignment:**
   - Circular reference check done in Python
   - Could use recursive CTEs for database-level validation

---

## Conclusion

The HRMS database schema is comprehensive and well-structured for an enterprise HR system. It supports:

✅ **Complete employee lifecycle** from onboarding to exit  
✅ **Flexible shift management** with time-bound assignments  
✅ **Dual-layer attendance** (raw events + processed records)  
✅ **Production-grade payroll** with detailed breakdowns  
✅ **Configurable leave management** with workflow approvals  
✅ **Multi-level approval workflows** for all modules  
✅ **Audit compliance** with immutable logs and locks  

**Recommended Next Steps:**
1. Centralize database credentials to environment variables
2. Migrate to Alembic for schema version control
3. Add database-level validation for manager hierarchy
4. Implement connection pooling for better performance
5. Add monitoring and query performance logging

---

**Document Version:** 1.0  
**Last Updated:** December 24, 2025  
**Schema Version:** Production-ready (Pre-Alembic)
