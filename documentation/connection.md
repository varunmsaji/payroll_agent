# Database Connection (`app/database/connection.py`)

## Overview
This module provides the database connection factory.

## Configuration
- **`DB_PARAMS`**: Dictionary containing database credentials (`dbname`, `user`, `password`, `host`, `port`).
- **Note**: Currently hardcoded. Recommended to move to environment variables.

## Functions

### `get_connection()`
- **Returns**: A new `psycopg2` connection object.
- **Usage**: Used by all other database modules to obtain a connection.
