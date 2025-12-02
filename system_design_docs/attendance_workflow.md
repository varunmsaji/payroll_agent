# Attendance Module - System Design & Workflow

## 1. Overview
The Attendance module is designed to be robust, audit-proof, and real-time. It uses an **Event-Sourcing inspired approach** where every action (check-in, break, check-out) is logged as an immutable raw event. These events are then processed to calculate the final daily attendance record (hours worked, status, overtime, etc.).

## 2. Architecture Layers

The system follows a clean 3-layer architecture:

1.  **API Layer (`app/api/attendence.py`)**
    *   **Role**: Entry point for HTTP requests.
    *   **Responsibilities**: Input validation, routing, and calling the Service layer.
    *   **Endpoints**:
        *   Actions: `/check-in`, `/check-out`, `/break/start`, `/break/end`
        *   Views: `/today/{id}`, `/employee/{id}` (history), `/company` (daily view)
        *   Admin: `/override/{id}`, `/lock/{id}`

2.  **Service Layer (`app/services/attendence_services.py`)**
    *   **Role**: Business Logic Core.
    *   **Responsibilities**:
        *   Validating state (e.g., preventing double check-ins).
        *   Logging raw events.
        *   **Triggering Recalculation**: The most critical function. Every time an event occurs, the entire day's attendance is re-computed from scratch based on all events for that day.
        *   Applying Policies: Late grace periods, overtime rules, shift timings.

3.  **Database Layer (`app/database/attendence.py`)**
    *   **Role**: Data Persistence.
    *   **Components**:
        *   `AttendanceEventDB`: Manages the `attendance_events` table (Raw Logs).
        *   `AttendanceDB`: Manages the `attendance` table (Consolidated Daily Records).

---

## 3. Workflow: What Happens When Attendance is Marked?

This is the step-by-step flow when a user triggers an action (e.g., Check-In).

### Step 1: API Request
*   **User Action**: Employee clicks "Check In" on the UI.
*   **Request**: `POST /hrms/attendance/check-in` with `employee_id`.
*   **API Layer**: Receives request, validates payload, calls `AttendanceService.check_in()`.

### Step 2: Service Validation & Event Logging
*   **Service Layer (`AttendanceService.check_in`)**:
    1.  **Validation**: Checks if the employee is *already* checked in. If yes, raises an error.
    2.  **Log Event**: Calls `AttendanceEventDB.add_event()` to insert a record into `attendance_events`.
        *   *Data*: `event_type='check_in'`, `timestamp=NOW()`, `source='manual'`.
    3.  **Trigger Recalculation**: Immediately calls `recalculate_for_date(employee_id, date)`.

### Step 3: The Recalculation Engine (`recalculate_for_date`)
This is the heart of the system. It runs after *every* event to ensure the daily record is always up-to-date.

1.  **Fetch Context**:
    *   **Policy**: Loads attendance policy (grace times, overtime rules) active for that specific date.
    *   **Shift**: Determines the employee's shift (Start/End times).
    *   **Leaves/Holidays**: Checks if the employee is on leave or if it's a holiday.

2.  **Fetch Raw Events**:
    *   Retrieves **ALL** events (`check_in`, `break_start`, `break_end`, `check_out`) for that employee within the shift window.

3.  **Compute Metrics**:
    *   **Work Hours**: Sums up time between `check_in` and `check_out`, subtracting breaks.
    *   **Break Hours**: Sums up time between `break_start` and `break_end`.
    *   **Lateness**: Compares first `check_in` with Shift Start Time + Grace Period.
    *   **Early Exit**: Compares last `check_out` with Shift End Time - Grace Period.
    *   **Overtime**: Checks if `net_hours` > `required_hours` (if enabled in policy).

4.  **Determine Status**:
    *   Based on `net_hours` vs `required_hours` (and policy fractions for Half Day/Full Day), assigns status:
        *   `Present`
        *   `Half Day`
        *   `Short Hours`
        *   `Absent` (if no events)

### Step 4: Upsert Daily Record
*   **Database Layer**: The calculated data object is sent to `AttendanceDB.upsert_full_attendance()`.
*   **Action**:
    *   If a record for that `(employee_id, date)` exists: **UPDATE** it.
    *   If not: **INSERT** a new record.
*   **Result**: The `attendance` table now reflects the latest state (e.g., `status='Present'`, `check_in='09:00'`, `net_hours=0.0`).

---

## 4. Key Features & Logic

### Dynamic Policy & History
*   The system supports **Policy History**. If you change the "Late Grace Period" today, it won't retroactively mark last month's employees as late.
*   `AttendancePolicyDB.get_policy_for_date(date)` fetches the policy that was active *on that specific date*.

### Shift Handling
*   **Night Shifts**: Automatically handles shifts that cross midnight (e.g., 10 PM to 6 AM). The system defines the "Shift Window" as spanning two calendar days.
*   **Flexible Shifts**: If no shift is assigned, it defaults to a standard 9-5 window.

### Payroll Locking
*   **Feature**: `is_payroll_locked` flag in the `attendance` table.
*   **Logic**: Once payroll is generated or an admin locks the day, **NO** further updates (check-ins, overrides) are allowed. The Service layer checks this flag before processing any changes.

### Manual Overrides
*   **Scenario**: Employee forgot to check out.
*   **Action**: HR uses the "Override" endpoint.
*   **Flow**: Updates the `attendance` table directly. Note that this *bypasses* the raw event log for the calculation, but the override itself is an explicit action. (Alternatively, a "manual correction" event could be added, but the current implementation supports direct table updates for corrections).

## 5. Data Model Summary

### `attendance_events` (Immutable Log)
| Column | Description |
| :--- | :--- |
| `id` | Unique Event ID |
| `employee_id` | Employee Reference |
| `event_type` | `check_in`, `check_out`, `break_start`, `break_end` |
| `event_time` | Exact Timestamp |
| `source` | `manual`, `biometric`, `system` |

### `attendance` (Daily Summary)
| Column | Description |
| :--- | :--- |
| `employee_id` | Employee Reference |
| `date` | Calendar Date |
| `check_in` | First check-in time |
| `check_out` | Last check-out time |
| `net_hours` | Actual hours worked |
| `status` | `Present`, `Absent`, `Half Day`, etc. |
| `is_late` | Boolean |
| `is_overtime` | Boolean |
| `is_payroll_locked`| Boolean (Prevents edits) |
