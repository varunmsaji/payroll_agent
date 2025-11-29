# Attendance Database (`app/database/attendence.py`)

## Overview
This module manages attendance tracking, including raw event logging and daily attendance processing.

## Class: `AttendanceEventDB`

### Methods
- **`add_event(employee_id, event_type, source, meta)`**: Logs a raw event (check_in, check_out, break_start, break_end).
- **`get_events_for_day(employee_id, target_date)`**: Fetches all events for a specific day.
- **`get_all_events_for_employee(employee_id)`**: Fetches all events for an employee, sorted by time.

## Class: `AttendanceDB`

### Methods

#### `process_attendance(employee_id, day)`
- **Description**: Core logic to calculate daily attendance stats.
- **Logic**:
    1.  Fetches raw events for the day.
    2.  Determines `check_in` (first event) and `check_out` (last event).
    3.  Calculates `actual_break_minutes` from break events.
    4.  **Auto-Grant Policy**: If `AUTO_GRANT_BREAK_IF_NO_PUNCH` is True and no break was recorded, it assumes the standard shift break was taken.
    5.  Calculates `late_minutes` and `overtime_minutes` based on the assigned shift.
    6.  Calculates `net_hours` = Total Hours - Excess Break - Late + Overtime.
    7.  Upserts the result into the `attendance` table.

#### `get_attendance(employee_id)`
- **Description**: Fetches processed attendance history for an employee.
- **Output**: List of daily attendance records with type conversion (Decimal to float).
