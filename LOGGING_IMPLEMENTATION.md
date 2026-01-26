# Logging System Implementation Summary

## ✅ What's Been Implemented

### 1. **Logging Configuration Module** (`app/utils/logging_config.py`)
- Comprehensive logging setup with automatic log rotation
- Separate log files for general logs and errors
- Detailed log format with timestamps, module names, line numbers, and function names
- Automatic log deletion when files exceed size limits

### 2. **Log Files Location**
All logs are saved in the `logs/` directory:
- **`logs/app.log`** - All application logs (DEBUG level and above)
- **`logs/error.log`** - Only ERROR and CRITICAL logs
- **Backup files**: Automatically created as `app.log.1`, `app.log.2`, etc.

### 3. **Automatic Log Rotation**
- **Max size per file**: 10 MB
- **Backup count**: 5 files
- **Total max storage**: ~50 MB for app logs + ~50 MB for error logs
- When a log file reaches 10 MB, it's automatically rotated and the oldest backup is deleted

### 4. **Integrated into Application**
- Main application (`app/api/main.py`) initialized with logging
- Example implementation in `app/api/face_recognition.py` shows best practices
- Logs application startup, shutdown, and router registration events

### 5. **Git Configuration**
- Added `logs/` directory to `.gitignore` to prevent log files from being committed

## 📊 Log Format Example

```
2026-01-26 18:31:21 - app.api.face_recognition - INFO - [face_recognition.py:53] - register_face() - Face registration request for employee_id: 123
2026-01-26 18:31:22 - app.api.face_recognition - DEBUG - [face_recognition.py:36] - validate_image() - Image size: 245678 bytes
2026-01-26 18:31:22 - app.api.face_recognition - INFO - [face_recognition.py:62] - register_face() - Face registered successfully for employee_id: 123
```

## 🚀 Quick Start

### Run your application:
```bash
cd /media/varun/varun/work/final_hr_agents_with_ui/payroll_agent/payroll_backend
uvicorn app.api.main:app --reload
```

### View logs in real-time:
```bash
# Watch all logs
tail -f logs/app.log

# Watch only errors
tail -f logs/error.log
```

## 📝 How to Add Logging to Other Files

Add these two lines at the top of any Python file where you want logging:

```python
from app.utils.logging_config import get_logger
logger = get_logger(__name__)
```

Then use throughout your code:

```python
logger.info(f"Processing employee {employee_id}")
logger.debug(f"Details: {some_variable}")
logger.warning("Something unexpected happened")
logger.error(f"Operation failed: {error}")
logger.exception("Full traceback will be logged")
```

## ⚙️ Configuration Options

### Change log level (in `app/api/main.py`):
- `logging.DEBUG` - Most verbose (default, recommended for development)
- `logging.INFO` - Normal operations (recommended for production)
- `logging.WARNING` - Only warnings and errors
- `logging.ERROR` - Only errors

### Adjust rotation settings (in `app/utils/logging_config.py`):
- `MAX_LOG_SIZE = 10 * 1024 * 1024` - Change to adjust max file size
- `BACKUP_COUNT = 5` - Change to keep more/fewer backup files

## 📚 Documentation

See `LOGGING_USAGE.md` for detailed usage examples and best practices.
