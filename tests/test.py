import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.attendence import AttendanceDB

result = AttendanceDB.get_by_employee_and_date(25, date.today())
print(result)
