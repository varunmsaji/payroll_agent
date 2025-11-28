# Shifts Database (`app/database/shifts_db.py`)

## Overview
This module handles CRUD operations for the `shifts` table, which defines the various work schedules available in the organization.

## Class: `ShiftDB`

### Methods

#### `add_shift(data)`
- **Input**: `data` (dict) with `shift_name`, `start_time`, `end_time`, `is_night_shift`, `break_start`, `break_end`, `break_minutes`.
- **Description**: Creates a new shift definition.

#### `get_all()`
- **Description**: Fetches all configured shifts.

#### `get_one(shift_id)`
- **Description**: Fetches details of a specific shift.

#### `update_shift(shift_id, data)`
- **Description**: Updates an existing shift definition.

#### `delete_shift(shift_id)`
- **Description**: Deletes a shift.
