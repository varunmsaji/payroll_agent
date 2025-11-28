# Database Initialization (`app/database/database.py`)

## Overview
This module is responsible for initializing the database schema. It defines the `create_tables` function which executes DDL statements to create all necessary tables if they do not exist.

## Functions

### `create_tables()`
- **Purpose**: Creates the core tables for the HRMS application.
- **Tables Created**:
    - `employees`: Stores employee details.
    - `shifts`: Stores shift definitions.
    - `employee_shifts`: Links employees to shifts.
    - `attendance_events`: Stores raw attendance punches.
    - `attendance`: Stores processed daily attendance.
    - `salary_structure`: Stores salary components.
    - `payroll`: Stores generated payroll records.

## Usage
Run this file directly to initialize the database:
```bash
python -m app.database.database
```
