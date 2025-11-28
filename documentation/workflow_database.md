# Workflow Database (`app/database/workflow_database.py`)

## Overview
This module implements a generic Approval Workflow Engine. It allows defining multi-step approval processes for any module (e.g., Leave, Expense, Onboarding).

## Schema
- **`workflows`**: Defines a workflow (e.g., "Leave Approval").
- **`workflow_steps`**: Defines steps (e.g., Step 1: Manager, Step 2: HR).
- **`approval_logs`**: Tracks the lifecycle of a specific request (e.g., Leave Request #101).
- **`request_status`**: Stores the current overall status of a request.

## Functions

### `create_workflow(...)`
- Defines a new workflow with ordered steps and roles.

### `start_workflow(module, request_id, workflow_id, employee_id)`
- **Purpose**: Initiates a workflow for a specific request.
- **Logic**:
    1.  Fetches the first step of the workflow.
    2.  Resolves the approver based on the role (e.g., finds the employee's manager).
    3.  Creates an entry in `approval_logs` with status 'pending'.

### `approve_step(module, request_id, remarks)`
- **Purpose**: Approves the current pending step.
- **Logic**:
    1.  Updates the current step in `approval_logs` to 'approved'.
    2.  Calls `move_to_next_step`.

### `move_to_next_step(module, request_id)`
- **Purpose**: Advances the workflow.
- **Logic**:
    1.  Checks if there is a next step.
    2.  **If Next Step Exists**: Resolves the next approver and creates a new 'pending' log.
    3.  **If Final Step**:
        - Updates `request_status` to 'approved'.
        - **Hook**: If module is 'leave', calls `LeaveRequestDB.approve_leave_transaction` to finalize the leave.

### `reject_step(...)`
- Marks the current step and the overall request as 'rejected'.
- **Hook**: If module is 'leave', updates leave status to 'rejected'.
