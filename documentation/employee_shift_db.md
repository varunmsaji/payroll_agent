# Employee Shift Database (`app/database/employee_shift_db.py`)

## Overview
This module manages the assignment of shifts to employees. It handles the `employee_shifts` table.

## Class: `EmployeeShiftDB`

### Methods

#### `assign_shift(employee_id, shift_id, effective_from)`
- **Description**: Assigns a shift to an employee starting from a specific date.

#### `get_shift_history(employee_id)`
- **Description**: Fetches the history of shift assignments for an employee.

#### `get_current_shift(employee_id)`
- **Description**: Fetches the currently active shift for an employee.
- **Logic**: Selects the assignment where `effective_to` is NULL or in the future, ordered by `effective_from` descending.
