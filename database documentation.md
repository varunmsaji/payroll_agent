# HRMS Database Documentation

## Overview

This document provides a detailed description of the database schema for the HRMS (Human Resource Management System) application. The database is designed for PostgreSQL and covers modules for Employee Management, Shift Management, Attendance Tracking, Leave Management, Payroll, and Approval Workflows.

## Table Summary

| Table Name | Description |
| :--- | :--- |
| **`employees`** | Stores core employee details such as personal info, designation, and base salary. |
| **`shifts`** | Defines various work shifts with start/end times and break configurations. |
| **`employee_shifts`** | Assigns shifts to employees with effective dates. |
| **`attendance_events`** | Logs raw attendance punches (check-in, check-out, breaks). |
| **`attendance`** | Stores processed daily attendance summaries including calculated hours and status. |
| **`salary_structure`** | Defines the detailed salary components (Basic, HRA, Allowances) for employees. |
| **`payroll`** | Stores monthly generated payroll data for employees. |
| **`leave_types`** | Configures different types of leaves (e.g., Paid Leave, Sick Leave). |
| **`employee_leave_balance`** | Tracks leave quotas, usage, and remaining balance for each employee per year. |
| **`leave_requests`** | Stores leave applications submitted by employees. |
| **`leave_history`** | Records historical data of approved leaves. |
| **`workflows`** | Defines approval workflows for different modules. |
| **`workflow_steps`** | Specifies the sequence of steps and roles involved in a workflow. |
| **`approval_logs`** | Logs actions taken by approvers at each step of a workflow. |
| **`request_status`** | Tracks the overall status of requests (e.g., leaves, reimbursements) undergoing approval. |

---

## Detailed Schema

### 1. `employees`
Core table storing employee information.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `employee_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the employee. |
| `first_name` | `VARCHAR(100)` | | Employee's first name. |
| `last_name` | `VARCHAR(100)` | | Employee's last name. |
| `email` | `VARCHAR(255)` | `UNIQUE` | Employee's email address. |
| `phone` | `VARCHAR(20)` | | Contact phone number. |
| `designation` | `VARCHAR(100)` | | Job title or designation. |
| `department` | `VARCHAR(100)` | | Department the employee belongs to. |
| `date_of_joining` | `DATE` | | Date when the employee joined the company. |
| `base_salary` | `NUMERIC(10,2)` | `NOT NULL` | Base salary amount. |
| `status` | `VARCHAR(20)` | `DEFAULT 'active'` | Employment status (e.g., active, inactive). |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 2. `shifts`
Defines work shifts and their timings.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `shift_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the shift. |
| `shift_name` | `VARCHAR(100)` | `NOT NULL` | Name of the shift (e.g., General, Morning). |
| `start_time` | `TIME` | `NOT NULL` | Shift start time. |
| `end_time` | `TIME` | `NOT NULL` | Shift end time. |
| `is_night_shift` | `BOOLEAN` | `DEFAULT FALSE` | Flag indicating if the shift spans overnight. |
| `break_start` | `TIME` | | Scheduled break start time. |
| `break_end` | `TIME` | | Scheduled break end time. |
| `break_minutes` | `INT` | `DEFAULT 0` | Duration of the break in minutes. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 3. `employee_shifts`
Maps employees to shifts.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the assignment. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee assigned to the shift. |
| `shift_id` | `INT` | `FK -> shifts(shift_id)` | The assigned shift. |
| `effective_from` | `DATE` | `NOT NULL` | Date from which the shift is effective. |
| `effective_to` | `DATE` | | Date until which the shift is effective (optional). |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 4. `attendance_events`
Log of raw punch events.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the event. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee involved in the event. |
| `event_type` | `VARCHAR(20)` | `NOT NULL` | Type of event (check_in, check_out, break_start, break_end). |
| `event_time` | `TIMESTAMP` | `NOT NULL` | Timestamp of the event. |
| `source` | `VARCHAR(40)` | `DEFAULT 'manual'` | Source of the punch (e.g., manual, biometric). |
| `meta` | `JSONB` | | Additional metadata for the event. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 5. `attendance`
Processed daily attendance records.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `attendance_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the attendance record. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee. |
| `date` | `DATE` | `NOT NULL` | The date of attendance. |
| `check_in` | `TIMESTAMP` | | First check-in time of the day. |
| `check_out` | `TIMESTAMP` | | Last check-out time of the day. |
| `total_hours` | `NUMERIC(5,2)` | | Total raw hours between check-in and check-out. |
| `net_hours` | `NUMERIC(5,2)` | | Net hours worked after deducting breaks/penalties. |
| `late_minutes` | `INT` | | Minutes late for the shift. |
| `overtime_minutes` | `INT` | | Overtime minutes worked. |
| `break_minutes` | `INT` | | Total break duration taken. |
| `shift_id` | `INT` | | ID of the shift applicable for this day. |
| `status` | `VARCHAR(20)` | `DEFAULT 'present'` | Attendance status. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |
| **Constraint** | | `UNIQUE(employee_id, date)` | One record per employee per day. |

### 6. `salary_structure`
Details of salary breakdown.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee. |
| `basic` | `NUMERIC(10,2)` | `NOT NULL` | Basic salary component. |
| `hra` | `NUMERIC(10,2)` | `NOT NULL` | House Rent Allowance. |
| `allowances` | `NUMERIC(10,2)` | `DEFAULT 0` | Other allowances. |
| `deductions` | `NUMERIC(10,2)` | `DEFAULT 0` | Standard deductions. |
| `effective_from` | `DATE` | `NOT NULL` | Start date for this salary structure. |
| `effective_to` | `DATE` | | End date for this salary structure. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 7. `payroll`
Monthly payroll records.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `payroll_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee. |
| `month` | `INT` | `NOT NULL` | Payroll month. |
| `year` | `INT` | `NOT NULL` | Payroll year. |
| `working_days` | `INT` | | Total working days in the month. |
| `present_days` | `INT` | | Days the employee was present. |
| `total_hours` | `NUMERIC(10,2)` | | Total hours worked in the month. |
| `gross_salary` | `NUMERIC(10,2)` | | Gross salary calculated. |
| `net_salary` | `NUMERIC(10,2)` | | Net salary after deductions. |
| `generated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Timestamp of payroll generation. |
| **Constraint** | | `UNIQUE(employee_id, month, year)` | One payroll record per employee per month. |

### 8. `leave_types`
Configuration for leave types.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `leave_type_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `name` | `VARCHAR(50)` | `NOT NULL` | Name of the leave type (e.g., Casual Leave). |
| `code` | `VARCHAR(10)` | `UNIQUE NOT NULL` | Short code (e.g., CL, SL). |
| `yearly_quota` | `INT` | `DEFAULT 0` | Default annual quota for this leave type. |
| `is_paid` | `BOOLEAN` | `DEFAULT TRUE` | Whether the leave is paid. |
| `carry_forward` | `BOOLEAN` | `DEFAULT TRUE` | Whether unused leave carries forward to next year. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 9. `employee_leave_balance`
Employee leave balances per year.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee. |
| `leave_type_id` | `INT` | `FK -> leave_types(leave_type_id)` | The leave type. |
| `year` | `INT` | `NOT NULL` | The year for the balance. |
| `total_quota` | `INT` | `NOT NULL` | Total leave quota allocated. |
| `used` | `INT` | `DEFAULT 0` | Number of leave days used. |
| `remaining` | `INT` | `NOT NULL` | Remaining leave balance. |
| `carry_forwarded` | `INT` | `DEFAULT 0` | Leaves carried forwarded from previous year. |
| **Constraint** | | `UNIQUE(employee_id, leave_type_id, year)` | Unique balance record per type/year. |

### 10. `leave_requests`
Applications for leave.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `leave_id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | Applicant employee. |
| `leave_type_id` | `INT` | `FK -> leave_types(leave_type_id)` | Requested leave type. |
| `start_date` | `DATE` | `NOT NULL` | Start date of leave. |
| `end_date` | `DATE` | `NOT NULL` | End date of leave. |
| `total_days` | `DECIMAL(5,2)` | `NOT NULL` | Duration of leave in days. |
| `reason` | `TEXT` | | Reason for leave. |
| `status` | `VARCHAR(20)` | `DEFAULT 'pending'` | Status (pending, approved, rejected). |
| `applied_on` | `TIMESTAMP` | `DEFAULT NOW()` | Application timestamp. |
| `approved_by` | `INT` | `FK -> employees(employee_id)` | Manager who approved/acted. |
| `approved_on` | `TIMESTAMP` | | Timestamp of approval/action. |

### 11. `leave_history`
History of approved leaves.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `employee_id` | `INT` | `FK -> employees(employee_id)` | The employee. |
| `leave_type_id` | `INT` | `FK -> leave_types(leave_type_id)` | The leave type. |
| `start_date` | `DATE` | `NOT NULL` | Start date. |
| `end_date` | `DATE` | `NOT NULL` | End date. |
| `total_days` | `DECIMAL(5,2)` | `NOT NULL` | Duration in days. |
| `recorded_on` | `TIMESTAMP` | `DEFAULT NOW()` | Timestamp when recorded. |

### 12. `workflows`
Definitions of approval workflows.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Name of the workflow. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Module this workflow applies to. |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Whether the workflow is active. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |

### 13. `workflow_steps`
Steps within a workflow.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `workflow_id` | `INT` | `FK -> workflows(id)` | Parent workflow. |
| `step_order` | `INT` | `NOT NULL` | Sequence number of the step. |
| `role` | `VARCHAR(50)` | `NOT NULL` | Role responsible for this step. |
| `is_final` | `BOOLEAN` | `DEFAULT FALSE` | Marks if this is the final approval step. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |
| **Constraint** | | `UNIQUE(workflow_id, step_order)` | Unique step order per workflow. |

### 14. `approval_logs`
Logs of approval actions.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Module name. |
| `request_id` | `INT` | `NOT NULL` | ID of the request being approved. |
| `workflow_id` | `INT` | `FK -> workflows(id)` | The workflow being followed. |
| `step_order` | `INT` | `NOT NULL` | The current step number. |
| `approver_id` | `INT` | `NOT NULL` | ID of the person approving. |
| `status` | `VARCHAR(20)` | `CHECK(pending, approved, rejected)` | Status of this step. |
| `acted_at` | `TIMESTAMP` | | Timestamp of action. |
| `remarks` | `TEXT` | | Comments or remarks. |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Record creation timestamp. |
| **Constraint** | | `UNIQUE(module, request_id, step_order)` | Unique log per step of a request. |

### 15. `request_status`
Current status of requests.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier. |
| `module` | `VARCHAR(50)` | `NOT NULL` | Module name. |
| `request_id` | `INT` | `NOT NULL` | ID of the request. |
| `status` | `VARCHAR(20)` | `CHECK(pending, approved, rejected)` | Overall status of the request. |
| `updated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Last update timestamp. |
| **Constraint** | | `UNIQUE(module, request_id)` | Unique status per request. |
