# Payroll Database (`app/database/payroll.py`)

## Overview
This module handles the generation and retrieval of monthly payroll records.

## Class: `PayrollDB`

### Methods

#### `generate(employee_id, month, year)`
- **Purpose**: Generates or updates the payroll record for a specific month.
- **Logic**:
    1.  Calculates total `net_hours` and `present_days` from the `attendance` table.
    2.  Fetches the latest `salary_structure` for the employee.
    3.  Calculates `gross_salary` (Basic + HRA + Allowances).
    4.  Calculates `net_salary` (Gross - Deductions).
    5.  Upserts the record into the `payroll` table.

#### `get_payroll(employee_id, month, year)`
- **Description**: Fetches the payroll record for a specific employee and month.
