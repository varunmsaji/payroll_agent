# Database Documentation

This document provides a comprehensive overview of the database architecture, schema, and operations for the HRMS application.

---

## 1. Database Initialization (`app/database/database.py`)

### Overview
This module is responsible for initializing the database schema. It defines the `create_tables` function which executes DDL statements to create all necessary tables if they do not exist.

### Functions

#### `create_tables()`
- **Purpose**: Creates the core tables for the HRMS application.
- **Tables Created**:
    - `employees`: Stores employee details.
    - `shifts`: Stores shift definitions.
    - `employee_shifts`: Links employees to shifts.
    - `attendance_events`: Stores raw attendance punches.
    - `attendance`: Stores processed daily attendance.
    - `salary_structure`: Stores salary components.
    - `payroll`: Stores generated payroll records.

### Usage
Run this file directly to initialize the database:
```bash
python -m app.database.database
```

---

## 2. Database Connection (`app/database/connection.py`)

### Overview
This module provides the database connection factory.

### Configuration
- **`DB_PARAMS`**: Dictionary containing database credentials (`dbname`, `user`, `password`, `host`, `port`).
- **Note**: Currently hardcoded. Recommended to move to environment variables.

### Functions

#### `get_connection()`
- **Returns**: A new `psycopg2` connection object.
- **Usage**: Used by all other database modules to obtain a connection.

---

## 3. Employee Database (`app/database/employee_db.py`)

### Overview
This module handles all database operations related to the `employees` table. It uses `psycopg2` with `RealDictCursor` to return dictionary-like objects.

### Class: `EmployeeDB`

#### Methods

##### `add_employee(data)`
- **Input**: `data` (dict) containing `first_name`, `last_name`, `email`, `phone`, `designation`, `department`, `date_of_joining`, `base_salary`, `manager_id`.
- **Output**: The created employee record.
- **Description**: Inserts a new employee into the database.

##### `get_all()`
- **Output**: List of all employees.
- **Description**: Fetches all employees, joining with the `employees` table (self-join) to fetch manager names.

##### `get_one(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: Single employee record or `None`.
- **Description**: Fetches details of a specific employee, including manager details.

##### `update_employee(employee_id, data)`
- **Input**: `employee_id` (int), `data` (dict)
- **Output**: Updated employee record.
- **Description**: Updates basic details and manager assignment for an employee.

##### `set_manager(employee_id, manager_id)`
- **Input**: `employee_id` (int), `manager_id` (int)
- **Output**: Updated employee record.
- **Description**: Updates only the `manager_id` for an employee.

##### `get_manager_id(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: `manager_id` (int) or `None`.
- **Description**: Helper to quickly fetch the manager's ID for workflow routing.

##### `get_all_managers()`
- **Output**: List of employees with 'manager', 'lead', or 'head' in their designation.
- **Description**: Used for populating manager selection dropdowns.

##### `delete_employee(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: `True`
- **Description**: Deletes an employee record.

##### `get_hr_user()`
- **Output**: `employee_id` (int) of the first found HR user.
- **Description**: Used for routing workflows to HR.

##### `get_finance_head()`
- **Output**: `employee_id` (int) of the Finance Head.
- **Description**: Used for routing workflows to Finance.

##### `get_director()`
- **Output**: `employee_id` (int) of the Director/CEO.
- **Description**: Used for routing workflows to the Director.

---

## 4. Shifts Database (`app/database/shifts_db.py`)

### Overview
This module handles CRUD operations for the `shifts` table, which defines the various work schedules available in the organization.

### Class: `ShiftDB`

#### Methods

##### `add_shift(data)`
- **Input**: `data` (dict) with `shift_name`, `start_time`, `end_time`, `is_night_shift`, `break_start`, `break_end`, `break_minutes`.
- **Description**: Creates a new shift definition.

##### `get_all()`
- **Description**: Fetches all configured shifts.

##### `get_one(shift_id)`
- **Description**: Fetches details of a specific shift.

##### `update_shift(shift_id, data)`
- **Description**: Updates an existing shift definition.

##### `delete_shift(shift_id)`
- **Description**: Deletes a shift.

---

## 5. Employee Shift Database (`app/database/employee_shift_db.py`)

### Overview
This module manages the assignment of shifts to employees. It handles the `employee_shifts` table.

### Class: `EmployeeShiftDB`

#### Methods

##### `assign_shift(employee_id, shift_id, effective_from)`
- **Description**: Assigns a shift to an employee starting from a specific date.

##### `get_shift_history(employee_id)`
- **Description**: Fetches the history of shift assignments for an employee.

##### `get_current_shift(employee_id)`
- **Description**: Fetches the currently active shift for an employee.
- **Logic**: Selects the assignment where `effective_to` is NULL or in the future, ordered by `effective_from` descending.

---

## 6. Attendance Database (`app/database/attendence.py`)

### Overview
This module manages attendance tracking, including raw event logging and daily attendance processing.

### Class: `AttendanceEventDB`

#### Methods
- **`add_event(employee_id, event_type, source, meta)`**: Logs a raw event (check_in, check_out, break_start, break_end).
- **`get_events_for_day(employee_id, target_date)`**: Fetches all events for a specific day.
- **`get_all_events_for_employee(employee_id)`**: Fetches all events for an employee, sorted by time.

### Class: `AttendanceDB`

#### Methods

##### `process_attendance(employee_id, day)`
- **Description**: Core logic to calculate daily attendance stats.
- **Logic**:
    1.  Fetches raw events for the day.
    2.  Determines `check_in` (first event) and `check_out` (last event).
    3.  Calculates `actual_break_minutes` from break events.
    4.  **Auto-Grant Policy**: If `AUTO_GRANT_BREAK_IF_NO_PUNCH` is True and no break was recorded, it assumes the standard shift break was taken.
    5.  Calculates `late_minutes` and `overtime_minutes` based on the assigned shift.
    6.  Calculates `net_hours` = Total Hours - Excess Break - Late + Overtime.
    7.  Upserts the result into the `attendance` table.

##### `get_attendance(employee_id)`
- **Description**: Fetches processed attendance history for an employee.
- **Output**: List of daily attendance records with type conversion (Decimal to float).

---

## 7. Leave Database (`app/database/leave_database.py`)

### Overview
This comprehensive module handles the entire Leave Management lifecycle, including Leave Types, Balances, Requests, and History.

### Classes

#### `LeaveTables`
- **`create_tables()`**: Creates `leave_types`, `employee_leave_balance`, `leave_requests`, and `leave_history` tables.

#### `LeaveTypeDB`
- **`add_leave_type(...)`**: Creates a new leave type (e.g., Sick Leave, Paid Leave).
- **`get_leave_types()`**: Lists all available leave types.

#### `LeaveBalanceDB`
- **`initialize_balance(...)`**: Assigns a leave quota to an employee for a specific year.
- **`get_balance(employee_id, year)`**: Fetches leave balances (quota, used, remaining).
- **`update_balance_used_safe(...)`**: Transactionally updates the used/remaining balance. Fails if insufficient balance.

#### `LeaveRequestDB`
- **`apply_leave(...)`**: Creates a new leave request with status 'pending'.
- **`approve_leave_transaction(leave_id, manager_id)`**:
    - **Critical Transaction**:
        1.  Locks the leave request row.
        2.  Updates status to 'approved'.
        3.  Checks if leave is PAID.
        4.  If PAID, deducts from `employee_leave_balance`.
        5.  Inserts record into `leave_history`.
    - **Rollback**: Automatically rolls back if any step fails.
- **`reject_leave(...)`**: Updates status to 'rejected'.
- **`list_requests(...)`**: Fetches requests (filtered by employee or all).

#### `LeaveHistoryDB`
- **`get_history(employee_id)`**: Fetches approved leave history.
- **`get_unpaid_leave_days(...)`**: Calculates total unpaid leave days for a given month (used for payroll).

---

## 8. Salary Database (`app/database/salary.py`)

### Overview
This module manages employee salary structures.

### Class: `SalaryDB`

#### Methods

##### `add_structure(employee_id, data)`
- **Input**: `data` containing `basic`, `hra`, `allowances`, `deductions`, `effective_from`.
- **Description**: Adds a new salary structure version for an employee.

##### `get_structure(employee_id)`
- **Description**: Fetches all salary structure history for an employee.

##### `get_salary_structure(employee_id)`
- **Description**: Alias for `get_structure`.

---

## 9. Payroll Database (`app/database/payroll.py`)

### Overview
This module handles the generation and retrieval of monthly payroll records.

### Class: `PayrollDB`

#### Methods

##### `generate(employee_id, month, year)`
- **Purpose**: Generates or updates the payroll record for a specific month.
- **Logic**:
    1.  Calculates total `net_hours` and `present_days` from the `attendance` table.
    2.  Fetches the latest `salary_structure` for the employee.
    3.  Calculates `gross_salary` (Basic + HRA + Allowances).
    4.  Calculates `net_salary` (Gross - Deductions).
    5.  Upserts the record into the `payroll` table.

##### `get_payroll(employee_id, month, year)`
- **Description**: Fetches the payroll record for a specific employee and month.

---

## 10. Workflow Database (`app/database/workflow_database.py`)

### Overview
This module implements a generic Approval Workflow Engine. It allows defining multi-step approval processes for any module (e.g., Leave, Expense, Onboarding).

### Schema
- **`workflows`**: Defines a workflow (e.g., "Leave Approval").
- **`workflow_steps`**: Defines steps (e.g., Step 1: Manager, Step 2: HR).
- **`approval_logs`**: Tracks the lifecycle of a specific request (e.g., Leave Request #101).
- **`request_status`**: Stores the current overall status of a request.

### Functions

#### `create_workflow(...)`
- Defines a new workflow with ordered steps and roles.

#### `start_workflow(module, request_id, workflow_id, employee_id)`
- **Purpose**: Initiates a workflow for a specific request.
- **Logic**:
    1.  Fetches the first step of the workflow.
    2.  Resolves the approver based on the role (e.g., finds the employee's manager).
    3.  Creates an entry in `approval_logs` with status 'pending'.

#### `approve_step(module, request_id, remarks)`
- **Purpose**: Approves the current pending step.
- **Logic**:
    1.  Updates the current step in `approval_logs` to 'approved'.
    2.  Calls `move_to_next_step`.

#### `move_to_next_step(module, request_id)`
- **Purpose**: Advances the workflow.
- **Logic**:
    1.  Checks if there is a next step.
    2.  **If Next Step Exists**: Resolves the next approver and creates a new 'pending' log.
    3.  **If Final Step**:
        - Updates `request_status` to 'approved'.
        - **Hook**: If module is 'leave', calls `LeaveRequestDB.approve_leave_transaction` to finalize the leave.

#### `reject_step(...)`
- Marks the current step and the overall request as 'rejected'.
- **Hook**: If module is 'leave', updates leave status to 'rejected'.

---

## 11. Mock Data Seeder (`app/database/mock_data_seeder.py`)

### Overview
This script populates the database with dummy data for testing and development purposes.

### Functions

- **`seed_employees(n=10)`**: Creates random employee records.
- **`seed_shifts()`**: Creates standard shifts (General, Morning, Evening, Night).
- **`assign_shifts()`**: Assigns random shifts to all employees.
- **`seed_attendance_events(days=7)`**: Generates random check-in/out events for the last 7 days.
- **`process_attendance_for_all(days=7)`**: Runs the daily attendance processing logic for the seeded events.
- **`seed_salary_structure()`**: Assigns random salary structures to employees.
- **`generate_payroll(month, year)`**: Generates payroll for the specified month.
- **`seed_leave_types()`**: Creates standard leave types (PL, SL, UL).
- **`seed_leave_balances()`**: Initializes leave quotas for all employees.
- **`seed_leave_requests()`**: Creates random leave requests (approved and pending) and generates history.

### Usage
Run the script directly to seed the database:
```bash
python -m app.database.mock_data_seeder
```
