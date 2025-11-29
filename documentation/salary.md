# Salary Database (`app/database/salary.py`)

## Overview
This module manages employee salary structures.

## Class: `SalaryDB`

### Methods

#### `add_structure(employee_id, data)`
- **Input**: `data` containing `basic`, `hra`, `allowances`, `deductions`, `effective_from`.
- **Description**: Adds a new salary structure version for an employee.

#### `get_structure(employee_id)`
- **Description**: Fetches all salary structure history for an employee.

#### `get_salary_structure(employee_id)`
- **Description**: Alias for `get_structure`.
