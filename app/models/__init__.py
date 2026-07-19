# import all models here for Alembic to find them
from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.branch import Branch
from app.models.company_setting import CompanySetting
from app.models.department import Department
from app.models.device import Device
from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument
from app.models.employee_shift_schedule import EmployeeShiftSchedule
from app.models.notification import Notification
from app.models.shift import Shift
from app.models.user import User

__all__ = [
    "AttendanceRecord",
    "AttendanceLog",
    "Branch",
    "CompanySetting",
    "Department",
    "Device",
    "Employee",
    "EmployeeDocument",
    "EmployeeShiftSchedule",
    "Notification",
    "Shift",
    "User",
]
