# Leave Database (`app/database/leave_database.py`)

## Overview
This comprehensive module handles the entire Leave Management lifecycle, including Leave Types, Balances, Requests, and History.

## Classes

### `LeaveTables`
- **`create_tables()`**: Creates `leave_types`, `employee_leave_balance`, `leave_requests`, and `leave_history` tables.

### `LeaveTypeDB`
- **`add_leave_type(...)`**: Creates a new leave type (e.g., Sick Leave, Paid Leave).
- **`get_leave_types()`**: Lists all available leave types.

### `LeaveBalanceDB`
- **`initialize_balance(...)`**: Assigns a leave quota to an employee for a specific year.
- **`get_balance(employee_id, year)`**: Fetches leave balances (quota, used, remaining).
- **`update_balance_used_safe(...)`**: Transactionally updates the used/remaining balance. Fails if insufficient balance.

### `LeaveRequestDB`
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

### `LeaveHistoryDB`
- **`get_history(employee_id)`**: Fetches approved leave history.
- **`get_unpaid_leave_days(...)`**: Calculates total unpaid leave days for a given month (used for payroll).
