# Mock Data Seeder (`app/database/mock_data_seeder.py`)

## Overview
This script populates the database with dummy data for testing and development purposes.

## Functions

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

## Usage
Run the script directly to seed the database:
```bash
python -m app.database.mock_data_seeder
```
