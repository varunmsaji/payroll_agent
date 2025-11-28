# Employee Database (`app/database/employee_db.py`)

## Overview
This module handles all database operations related to the `employees` table. It uses `psycopg2` with `RealDictCursor` to return dictionary-like objects.

## Class: `EmployeeDB`

### Methods

#### `add_employee(data)`
- **Input**: `data` (dict) containing `first_name`, `last_name`, `email`, `phone`, `designation`, `department`, `date_of_joining`, `base_salary`, `manager_id`.
- **Output**: The created employee record.
- **Description**: Inserts a new employee into the database.

#### `get_all()`
- **Output**: List of all employees.
- **Description**: Fetches all employees, joining with the `employees` table (self-join) to fetch manager names.

#### `get_one(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: Single employee record or `None`.
- **Description**: Fetches details of a specific employee, including manager details.

#### `update_employee(employee_id, data)`
- **Input**: `employee_id` (int), `data` (dict)
- **Output**: Updated employee record.
- **Description**: Updates basic details and manager assignment for an employee.

#### `set_manager(employee_id, manager_id)`
- **Input**: `employee_id` (int), `manager_id` (int)
- **Output**: Updated employee record.
- **Description**: Updates only the `manager_id` for an employee.

#### `get_manager_id(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: `manager_id` (int) or `None`.
- **Description**: Helper to quickly fetch the manager's ID for workflow routing.

#### `get_all_managers()`
- **Output**: List of employees with 'manager', 'lead', or 'head' in their designation.
- **Description**: Used for populating manager selection dropdowns.

#### `delete_employee(employee_id)`
- **Input**: `employee_id` (int)
- **Output**: `True`
- **Description**: Deletes an employee record.

#### `get_hr_user()`
- **Output**: `employee_id` (int) of the first found HR user.
- **Description**: Used for routing workflows to HR.

#### `get_finance_head()`
- **Output**: `employee_id` (int) of the Finance Head.
- **Description**: Used for routing workflows to Finance.

#### `get_director()`
- **Output**: `employee_id` (int) of the Director/CEO.
- **Description**: Used for routing workflows to the Director.
