from abc import ABC, abstractmethod
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.employee import Employee

class AttendancePolicy(ABC):
    @abstractmethod
    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        pass

    @abstractmethod
    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        pass

    @abstractmethod
    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        pass

    @abstractmethod
    def supports_shift_system(self) -> bool:
        pass

    @abstractmethod
    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        pass

    @abstractmethod
    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        pass

    def apply_shift_metrics(self, record: Any) -> None:
        """Apply shift metrics (units/category) to the attendance record if applicable."""
        record.shift_category = None
        record.shift_units = 0.0


class DefaultAttendancePolicy(AttendancePolicy):
    def __init__(self):
        self.default_start_time = time(9, 0)
        self.default_late_grace_minutes = 15

    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        start_time = datetime.combine(check_in_time.date(), self.default_start_time)
        late_threshold = start_time.timestamp() + (self.default_late_grace_minutes * 60)
        return check_in_time.timestamp() > late_threshold

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        start_time = datetime.combine(check_in_time.date(), self.default_start_time)
        if check_in_time > start_time:
            return int((check_in_time - start_time).total_seconds() / 60)
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)

    def supports_shift_system(self) -> bool:
        return True

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        return False

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        return None


class LeatherDepartmentPolicy(AttendancePolicy):
    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return False

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)

    def supports_shift_system(self) -> bool:
        return False

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        return False

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        return None


class UnifiedDepartmentPolicy(AttendancePolicy):
    """
    Unified policy for Reception and Workers departments.
    Features:
    - Department-level shift settings
    - Employee shift schedules (rotating shifts)
    - Weekly rest days
    - Working on rest day support
    - Late calculation
    - Shift deficit calculation
    - Overtime calculation (optional)
    """
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return self.calculate_late_minutes(db, employee, check_in_time) > 0

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        if not employee.department:
            return 0
        
        # Check if it's a rest day
        if self.is_rest_day(db, employee, check_in_time.date()):
            return 0
        
        # Determine which shift type we're using (morning or evening)
        shift = self.get_shift_for_day(db, employee, check_in_time.date())
        shift_type = None
        if shift and "type" in shift:
            shift_type = shift.get("type")
        
        # Get appropriate late start time based on shift type
        late_start = employee.department.late_start_time  # Default to morning shift
        
        # Check if it's evening shift and evening shift settings are available
        if shift_type in ["evening", "مسائي"] and employee.department.evening_shift_late_start_time:
            late_start = employee.department.evening_shift_late_start_time
        
        start_time = datetime.combine(check_in_time.date(), late_start)
        
        if check_in_time.timestamp() > start_time.timestamp():
            return int((check_in_time.timestamp() - start_time.timestamp()) / 60)
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)
    
    def calculate_overtime_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        """Calculate overtime hours based on department settings"""
        if not employee.department or not employee.department.overtime_enabled:
            return 0.0
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        shift_hours = employee.department.shift_hours or 7
        
        if working_hours > shift_hours:
            return round(working_hours - shift_hours, 2)
        return 0.0
    
    def calculate_shift_deficit_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        """Calculate shift deficit hours if working hours are less than required"""
        if not employee.department:
            return 0.0
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        shift_hours = employee.department.shift_hours or 7
        
        if working_hours < shift_hours:
            return round(shift_hours - working_hours, 2)
        return 0.0

    def supports_shift_system(self) -> bool:
        return True

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        if not employee.weekly_rest_day:
            return False
        check_day = self.DAY_NAMES[check_date.weekday()]
        return check_day.lower() == employee.weekly_rest_day.lower()

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        if not employee.department:
            return None
            
        return {
            "shift_start": employee.department.shift_start_time,
            "shift_end": employee.department.shift_end_time,
            "shift_hours": employee.department.shift_hours,
            "late_start": employee.department.late_start_time,
            "overtime_start": employee.department.overtime_start_time,
            "evening_shift_start": employee.department.evening_shift_start_time,
            "evening_shift_end": employee.department.evening_shift_end_time,
            "evening_shift_hours": employee.department.evening_shift_hours,
            "evening_shift_late_start": employee.department.evening_shift_late_start_time,
        }


class ReceptionDepartmentPolicy(UnifiedDepartmentPolicy):
    """Reception department policy - same as unified policy"""
    pass


class WorkersDepartmentPolicy(AttendancePolicy):
    """Workers department policy - Independent policy with:
    - Auto-shift detection based on first check-in time
    - Grace-period-based late calculation (delay counted AFTER grace end)
    - Shift end based deficit/overtime calculation
    - Weekly rest day support (unlike CallCenter)
    """
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def _resolve_shift_category(self, employee: Employee, check_in_time: datetime) -> str:
        if not employee.department:
            return "workers_shift_1"
        shift_2_start = employee.department.evening_shift_start_time
        if shift_2_start and check_in_time.time() >= shift_2_start:
            return "workers_shift_2"
        return "workers_shift_1"

    def _resolve_shift_window(self, employee: Employee, check_in_time: datetime) -> Dict[str, time]:
        if not employee.department:
            return {
                "start_time": time(0, 0),
                "grace_end_time": time(0, 0),
                "end_time": time(23, 59, 59),
            }

        department = employee.department
        shift_category = self._resolve_shift_category(employee, check_in_time)

        if shift_category == "workers_shift_2" and all(
            [
                department.evening_shift_start_time,
                department.evening_shift_late_start_time,
                department.evening_shift_end_time,
            ]
        ):
            return {
                "start_time": department.evening_shift_start_time,
                "grace_end_time": department.evening_shift_late_start_time,
                "end_time": department.evening_shift_end_time,
            }

        return {
            "start_time": department.shift_start_time,
            "grace_end_time": department.late_start_time,
            "end_time": department.shift_end_time,
        }

    def get_shift_category_for_check_in(self, db: Session, employee: Employee, check_in_time: datetime) -> str:
        return self._resolve_shift_category(employee, check_in_time)

    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return self.calculate_late_minutes(db, employee, check_in_time) > 0

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        # If it's a rest day, no late penalty
        if self.is_rest_day(db, employee, check_in_time.date()):
            return 0
        window = self._resolve_shift_window(employee, check_in_time)
        grace_end_at = datetime.combine(check_in_time.date(), window["grace_end_time"])
        # Late = only minutes AFTER grace_end (NOT shift_start) - matches user spec
        if check_in_time > grace_end_at:
            return int((check_in_time - grace_end_at).total_seconds() // 60)
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)

    def calculate_overtime_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        window = self._resolve_shift_window(employee, check_in_time)
        shift_end_at = datetime.combine(check_in_time.date(), window["end_time"])
        if check_out_time <= shift_end_at:
            return 0.0
        return round((check_out_time - shift_end_at).total_seconds() / 3600, 2)

    def calculate_shift_deficit_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        window = self._resolve_shift_window(employee, check_in_time)
        shift_end_at = datetime.combine(check_in_time.date(), window["end_time"])
        if check_out_time >= shift_end_at:
            return 0.0
        return round((shift_end_at - check_out_time).total_seconds() / 3600, 2)

    def supports_shift_system(self) -> bool:
        return True

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        if not employee.weekly_rest_day:
            return False
        check_day = self.DAY_NAMES[check_date.weekday()]
        return check_day.lower() == employee.weekly_rest_day.lower()

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        if not employee.department:
            return None
        return {
            "shift_1": {
                "start_time": employee.department.shift_start_time,
                "grace_end_time": employee.department.late_start_time,
                "end_time": employee.department.shift_end_time,
            },
            "shift_2": {
                "start_time": employee.department.evening_shift_start_time,
                "grace_end_time": employee.department.evening_shift_late_start_time,
                "end_time": employee.department.evening_shift_end_time,
            },
        }

class CallCenterDepartmentPolicy(WorkersDepartmentPolicy):
    """Call center department policy - Mirrors Workers department but for Call Center"""
    def _resolve_shift_category(self, employee: Employee, check_in_time: datetime) -> str:
        if not employee.department:
            return "call_center_shift_1"
        shift_2_start = employee.department.evening_shift_start_time
        if shift_2_start and check_in_time.time() >= shift_2_start:
            return "call_center_shift_2"
        return "call_center_shift_1"


class DoctorsDepartmentPolicy(AttendancePolicy):
    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return self.calculate_late_minutes(db, employee, check_in_time) > 0

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        if not employee.department:
            return 0
        
        # Use department's new shift settings
        late_start = getattr(employee.department, 'late_start_time', time(8, 30))
        start_time = datetime.combine(check_in_time.date(), late_start)
        
        if check_in_time.timestamp() > start_time.timestamp():
            return int((check_in_time.timestamp() - start_time.timestamp()) / 60)
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)
    
    def calculate_overtime_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        if not employee.department:
            return 0.0
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        # For doctors: full shift is double half shift, so use 2 * shift hours as full shift
        half_shift_hours = getattr(employee.department, 'shift_hours', 7)
        full_shift_hours = half_shift_hours * 2
        
        if working_hours > full_shift_hours:
            return round(working_hours - full_shift_hours, 2)
        return 0.0
    
    def calculate_shift_deficit_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        if not employee.department:
            return 0.0
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        # Minimum is half shift
        half_shift_hours = getattr(employee.department, 'shift_hours', 7)
        
        if working_hours < half_shift_hours:
            return round(half_shift_hours - working_hours, 2)
        return 0.0
    
    def get_shift_type(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> str:
        if not employee.department:
            return "half_shift"
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        half_shift_hours = getattr(employee.department, 'shift_hours', 7)
        full_shift_hours = half_shift_hours * 2
        
        if working_hours >= full_shift_hours:
            return "full_shift"
        elif working_hours >= half_shift_hours:
            return "half_shift"
        return "incomplete"

    def supports_shift_system(self) -> bool:
        return True

    def apply_shift_metrics(self, record: Any) -> None:
        if not record.employee or not record.check_in_time or not record.check_out_time:
            record.shift_category = None
            record.shift_units = 0.0
            return
            
        raw_shift_type = self.get_shift_type(record.employee, record.check_in_time, record.check_out_time)
        shift_type_map = {
            "شفت كامل": "full_shift",
            "نصف شيفت": "half_shift",
            "نقص في الشفت": "incomplete",
        }
        shift_type = shift_type_map.get(raw_shift_type, raw_shift_type)
        record.shift_category = shift_type

        if shift_type == "full_shift":
            record.shift_units = 1.0  # Full shift is one unit
        elif shift_type == "half_shift":
            record.shift_units = 0.5  # Half shift is 0.5 units
        else:
            record.shift_units = 0.0

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        return False

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        if not employee.department:
            return None
        
        # Use new settings
        return {
            "shift_start": getattr(employee.department, 'shift_start_time', time(8, 0)),
            "shift_end": getattr(employee.department, 'shift_end_time', time(15, 0)),
            "shift_hours": getattr(employee.department, 'shift_hours', 7),
            "late_start": getattr(employee.department, 'late_start_time', time(8, 30)),
            "overtime_start": getattr(employee.department, 'overtime_start_time', time(15, 0)),
        }


class AttendancePolicyFactory:
    _policies = {
        "default": DefaultAttendancePolicy,
        "leather_department": LeatherDepartmentPolicy,
        "reception_department": ReceptionDepartmentPolicy,
        "doctors_department": DoctorsDepartmentPolicy,
        "workers_department": WorkersDepartmentPolicy,
        "call_center_department": CallCenterDepartmentPolicy,
    }

    @classmethod
    def get_policy(cls, policy_name: str) -> AttendancePolicy:
        policy_class = cls._policies.get(policy_name, DefaultAttendancePolicy)
        return policy_class()

    @classmethod
    def get_policy_for_employee(cls, db: Session, employee: Employee) -> AttendancePolicy:
        if employee.department:
            return cls.get_policy(employee.department.attendance_policy)
        return cls.get_policy("default")
