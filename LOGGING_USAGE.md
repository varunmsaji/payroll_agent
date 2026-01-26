# Logging Usage Guide

## Overview
The application now includes a comprehensive logging system with automatic log rotation. Logs are stored in the `logs/` directory and will automatically rotate when they reach 10 MB in size.

## Log Files
- **`logs/app.log`** - Contains all application logs (DEBUG and above)
- **`logs/error.log`** - Contains only ERROR and CRITICAL logs
- **Rotation**: Each log file keeps 5 backup copies (e.g., `app.log.1`, `app.log.2`, etc.)
- **Total Max Size**: ~50 MB for app logs, ~50 MB for error logs

## How to Use Logging in Your Code

### 1. Import the logger in any module:
```python
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
```

### 2. Use different log levels:
```python
# Debug - detailed information for troubleshooting
logger.debug(f"Processing employee ID: {employee_id}")

# Info - general informational messages
logger.info(f"Successfully registered face for employee {employee_id}")

# Warning - something unexpected but not critical
logger.warning(f"Employee {employee_id} attempted early check-in")

# Error - an error occurred but application continues
logger.error(f"Failed to process attendance for {employee_id}: {error_msg}")

# Critical - severe error that may cause application failure
logger.critical("Database connection lost!")
```

### 3. Log exceptions with full traceback:
```python
from app.utils.logging_config import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Your code here
    result = process_face_recognition(image)
except Exception as e:
    log_exception(logger, "Face recognition failed", e)
    # or simply:
    logger.exception("Face recognition failed")
```

## Example: Adding Logging to an API Endpoint

```python
from fastapi import APIRouter, HTTPException
from app.utils.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/faces/punch")
async def face_punch(employee_id: str, image: bytes):
    logger.info(f"Received punch request for employee: {employee_id}")
    logger.debug(f"Image size: {len(image)} bytes")
    
    try:
        result = await process_attendance(employee_id, image)
        logger.info(f"Attendance marked successfully for {employee_id}: {result}")
        return result
    except ValueError as e:
        logger.warning(f"Invalid data for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing attendance for {employee_id}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Configuration

### Change Log Level
Edit `app/api/main.py`:
```python
# Set to DEBUG for detailed logs (recommended for development)
setup_logging(log_level=logging.DEBUG)

# Set to INFO for normal operation (recommended for production)
setup_logging(log_level=logging.INFO)

# Set to WARNING to only log warnings and errors
setup_logging(log_level=logging.WARNING)
```

### Adjust Log Rotation Settings
Edit `app/utils/logging_config.py`:
```python
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB (change this value)
BACKUP_COUNT = 5  # Keep 5 backup files (change this value)
```

## Benefits

✅ **Automatic Rotation**: Old logs are automatically deleted when size limit is reached  
✅ **Separate Error Logs**: Easy to find and review errors without searching through all logs  
✅ **Detailed Context**: Every log includes timestamp, module, line number, and function name  
✅ **Console + File**: Logs appear in console (INFO+) and saved to files (DEBUG+)  
✅ **No Manual Cleanup**: The rotating handler manages log files automatically  

## Viewing Logs

```bash
# View latest logs
tail -f logs/app.log

# View only errors
tail -f logs/error.log

# Search logs for specific employee
grep "employee_123" logs/app.log

# View last 100 lines
tail -n 100 logs/app.log
```
