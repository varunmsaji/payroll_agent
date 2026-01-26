# app/services/attendance/exceptions.py


class AttendanceError(Exception):
    pass


class AlreadyCheckedIn(AttendanceError):
    pass


class NoActiveCheckIn(AttendanceError):
    pass


class BreakAlreadyRunning(AttendanceError):
    pass


class NoActiveBreak(AttendanceError):
    pass


class AttendanceLocked(AttendanceError):
    pass


# =====================================================
# Attendance rule exceptions (used by process_punch)
# =====================================================


class AttendanceException(Exception):
    """Base attendance exception"""


class AttendanceRejected(AttendanceException):
    """Business-rule rejection"""


class EarlyPunchNotAllowed(AttendanceException):
    """Early check-in violation"""
