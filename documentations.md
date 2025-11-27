# HRMS Database Documentation

This document provides a detailed overview of the database schema for the HRMS (Human Resource Management System). The database is PostgreSQL-based and is organized into three main modules:

1.  **Core HR & Payroll** (Employees, Shifts, Attendance, Payroll)
2.  **Leave Management** (Leave Types, Balances, Requests)
3.  **Workflow & Approvals** (Dynamic Approval Flows)

---

## 1. Core HR & Payroll Module

Defined in `app/database/database.py`.

### `employees`
Stores core employee information.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `employee_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the employee. |
| `first_name` | `VARCHAR(100)` | | First name. |
| `last_name` | `VARCHAR(100)` | | Last name. |
| `email` | `VARCHAR(255)` | `UNIQUE` | Official email address. |
| `phone` | `VARCHAR(20)` | | Contact number. |
| `designation` | `VARCHAR(100)` | | Job title. |
| `department` | `VARCHAR(100)` | | Department name. |
| `date_of_joining` | `DATE` | | Date of joining. |
| `base_salary` | `NUMERIC(10,2)` | `NOT NULL` | Base salary figure. |
| `status` | `VARCHAR(20)` | `DEFAULT 'active'` | Employment status (active, resigned, etc.). |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |
| `manager_id` | `INT` | `FK -> employees(employee_id)` | Self-referencing FK for the reporting manager. |

### `shifts`
Defines available work shifts.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `shift_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the shift. |
| `shift_name` | `VARCHAR(100)` | `NOT NULL` | Name of the shift (e.g., "General Shift"). |
| `start_time` | `TIME` | `NOT NULL` | Shift start time. |
| `end_time` | `TIME` | `NOT NULL` | Shift end time. |
| `is_night_shift` | `BOOLEAN` | `DEFAULT FALSE` | Flag for night shifts. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### `employee_shifts`
Maps employees to shifts over time.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique record ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `shift_id` | `INT` | `FK -> shifts` | The assigned shift. |
| `effective_from` | `DATE` | `NOT NULL` | Start date of this shift assignment. |
| `effective_to` | `DATE` | | End date (NULL means currently active). |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### `attendance_events`
Raw logs of attendance actions (punch-in, punch-out).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | `SERIAL` | `PRIMARY KEY` | Unique event ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `event_type` | `VARCHAR(20)` | `NOT NULL` | Type: `check_in`, `check_out`, `break_start`, `break_end`. |
| `event_time` | `TIMESTAMP` | `NOT NULL` | Exact time of the event. |
| `source` | `VARCHAR(40)` | `DEFAULT 'manual'` | Source of punch (e.g., 'biometric', 'web', 'manual'). |
| `meta` | `JSONB` | | Additional metadata (location, device info). |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### `attendance`
Processed daily attendance records.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `attendance_id` | `SERIAL` | `PRIMARY KEY` | Unique record ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `date` | `DATE` | `NOT NULL` | The date of attendance. |
| `check_in` | `TIMESTAMP` | | First check-in time. |
| `check_out` | `TIMESTAMP` | | Last check-out time. |
| `total_hours` | `NUMERIC(5,2)` | | Total working hours calculated. |
| `status` | `VARCHAR(20)` | `DEFAULT 'present'` | Status: `present`, `absent`, `half-day`, etc. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |
| **Constraint** | `UNIQUE` | `(employee_id, date)` | One record per employee per day. |

### `salary_structure`
Detailed breakdown of an employee's salary.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique record ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `basic` | `NUMERIC(10,2)` | `NOT NULL` | Basic pay component. |
| `hra` | `NUMERIC(10,2)` | `NOT NULL` | House Rent Allowance. |
| `allowances` | `NUMERIC(10,2)` | `DEFAULT 0` | Other allowances. |
| `deductions` | `NUMERIC(10,2)` | `DEFAULT 0` | Deductions (Tax, PF, etc.). |
| `effective_from` | `DATE` | `NOT NULL` | Validity start date. |
| `effective_to` | `DATE` | | Validity end date. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### `payroll`
Monthly generated payroll records.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `payroll_id` | `SERIAL` | `PRIMARY KEY` | Unique payroll ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `month` | `INT` | `NOT NULL` | Payroll month (1-12). |
| `year` | `INT` | `NOT NULL` | Payroll year. |
| `working_days` | `INT` | | Total working days in the month. |
| `present_days` | `INT` | | Days the employee was present. |
| `total_hours` | `NUMERIC(10,2)` | | Total hours worked. |
| `gross_salary` | `NUMERIC(10,2)` | | Calculated gross salary. |
| `net_salary` | `NUMERIC(10,2)` | | Final net salary payable. |
| `generated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Generation timestamp. |
| **Constraint** | `UNIQUE` | `(employee_id, month, year)` | One payroll record per employee per month. |

---

## 2. Leave Management Module

Defined in `app/database/leave_database.py`.

### `leave_types`
Configuration of different types of leaves.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `leave_type_id` | `SERIAL` | `PRIMARY KEY` | Unique ID. |
| `name` | `VARCHAR(50)` | `NOT NULL` | Name (e.g., "Sick Leave"). |
| `code` | `VARCHAR(10)` | `UNIQUE NOT NULL` | Short code (e.g., "SL"). |
| `yearly_quota` | `INT` | `DEFAULT 0` | Default annual quota. |
| `is_paid` | `BOOLEAN` | `DEFAULT TRUE` | Whether it's a paid leave. |
| `carry_forward` | `BOOLEAN` | `DEFAULT TRUE` | Can balance be carried forward? |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp. |

### `employee_leave_balance`
Tracks leave quota and usage for each employee.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `leave_type_id` | `INT` | `FK -> leave_types` | The leave type. |
| `year` | `INT` | `NOT NULL` | The year for this balance. |
| `total_quota` | `INT` | `NOT NULL` | Total assigned days. |
| `used` | `INT` | `DEFAULT 0` | Days used so far. |
| `remaining` | `INT` | `NOT NULL` | Days remaining. |
| `carry_forwarded` | `INT` | `DEFAULT 0` | Days brought from previous year. |
| **Constraint** | `UNIQUE` | `(employee_id, leave_type_id, year)` | Unique balance per type per year. |

### `leave_requests`
Applications for leave submitted by employees.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `leave_id` | `SERIAL` | `PRIMARY KEY` | Unique request ID. |
| `employee_id` | `INT` | `FK -> employees` | The applicant. |
| `leave_type_id` | `INT` | `FK -> leave_types` | Type of leave requested. |
| `start_date` | `DATE` | `NOT NULL` | Start date. |
| `end_date` | `DATE` | `NOT NULL` | End date. |
| `total_days` | `DECIMAL(5,2)` | `NOT NULL` | Duration in days. |
| `reason` | `TEXT` | | Reason for leave. |
| `status` | `VARCHAR(20)` | `DEFAULT 'pending'` | `pending`, `approved`, `rejected`. |
| `applied_on` | `TIMESTAMP` | `DEFAULT NOW()` | Application timestamp. |
| `approved_by` | `INT` | `FK -> employees` | Manager who approved/rejected. |
| `approved_on` | `TIMESTAMP` | | Timestamp of approval/rejection. |

### `leave_history`
Audit log of approved leaves.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique ID. |
| `employee_id` | `INT` | `FK -> employees` | The employee. |
| `leave_type_id` | `INT` | `FK -> leave_types` | The leave type. |
| `start_date` | `DATE` | `NOT NULL` | Start date. |
| `end_date` | `DATE` | `NOT NULL` | End date. |
| `total_days` | `DECIMAL(5,2)` | `NOT NULL` | Duration. |
| `recorded_on` | `TIMESTAMP` | `DEFAULT NOW()` | Recording timestamp. |

---

## 3. Workflow & Approvals Module

Defined in `app/database/workflow_database.py`.

### `workflows`
Defines approval workflows for different modules.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique workflow ID. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Workflow name. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Target module (e.g., 'leave', 'expense'). |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Is this workflow active? |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp. |

### `workflow_steps`
Steps involved in a specific workflow.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique step ID. |
| `workflow_id` | `INT` | `FK -> workflows` | Parent workflow. |
| `step_order` | `INT` | `NOT NULL` | Sequence number (1, 2, 3...). |
| `role` | `VARCHAR(50)` | `NOT NULL` | Role required to approve (e.g., 'manager', 'hr'). |
| `is_final` | `BOOLEAN` | `DEFAULT FALSE` | Is this the final approval step? |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp. |
| **Constraint** | `UNIQUE` | `(workflow_id, step_order)` | Unique step order per workflow. |

### `approval_logs`
Tracks the progress of a specific request through the workflow.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique log ID. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Module name. |
| `request_id` | `INT` | `NOT NULL` | ID of the request (e.g., `leave_id`). |
| `workflow_id` | `INT` | `FK -> workflows` | The workflow being followed. |
| `step_order` | `INT` | `NOT NULL` | Current step number. |
| `approver_id` | `INT` | `NOT NULL` | Employee ID of the assigned approver. |
| `status` | `VARCHAR(20)` | `CHECK (...)` | `pending`, `approved`, `rejected`. |
| `acted_at` | `TIMESTAMP` | | When the action was taken. |
| `remarks` | `TEXT` | | Approver's comments. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp. |
| **Constraint** | `UNIQUE` | `(module, request_id, step_order)` | Unique log per step per request. |

### `request_status`
Quick lookup for the overall status of a request.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique ID. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Module name. |
| `request_id` | `INT` | `NOT NULL` | ID of the request. |
| `status` | `VARCHAR(20)` | `CHECK (...)` | `pending`, `approved`, `rejected`. |
| `updated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Last update timestamp. |
| **Constraint** | `UNIQUE` | `(module, request_id)` | One status record per request. |
