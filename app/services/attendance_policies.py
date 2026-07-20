from abc import ABC, abstractmethod
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_shift_schedule import EmployeeShiftSchedule
from app.models.shift import Shift


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


class DefaultAttendancePolicy(AttendancePolicy):
    def __init__(self):
        from app.models.company_setting import CompanySetting
        self.CompanySetting = CompanySetting

    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        settings = db.query(self.CompanySetting).first()
        if not settings or not settings.work_start_time:
            return False
        start_time = datetime.combine(check_in_time.date(), settings.work_start_time)
        late_threshold = start_time.timestamp() + (settings.late_grace_minutes * 60)
        return check_in_time.timestamp() > late_threshold

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        settings = db.query(self.CompanySetting).first()
        if not settings or not settings.work_start_time:
            return 0
        start_time = datetime.combine(check_in_time.date(), settings.work_start_time)
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
        if employee.shift:
            return {
                "id": employee.shift.id,
                "name": employee.shift.name,
                "start_time": employee.shift.start_time,
                "end_time": employee.shift.end_time,
                "grace_period_minutes": employee.shift.grace_period_minutes,
            }
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
        """
        Get shift information for a specific day.
        Priority:
        1. Employee shift schedule for the specific day
        2. Employee default shift
        3. Department default settings
        """
        if not employee.department:
            return None
        
        # Check employee shift schedule first
        check_day = self.DAY_NAMES[check_date.weekday()]
        schedule = db.query(EmployeeShiftSchedule).filter(
            EmployeeShiftSchedule.employee_id == employee.id,
            EmployeeShiftSchedule.day_of_week == check_day.lower()
        ).first()
        
        shift = None
        shift_type = None
        
        if schedule:
            if schedule.shift_id:
                shift = db.query(Shift).filter(Shift.id == schedule.shift_id).first()
            shift_type = schedule.shift_type
            
            # Fallback to default shifts by name if shift not found
            if not shift:
                if shift_type in ["morning", "صباحي"]:
                    shift = db.query(Shift).filter(Shift.name == "صباحي").first()
                elif shift_type in ["evening", "مسائي"]:
                    shift = db.query(Shift).filter(Shift.name == "مسائي").first()
        
        # Fallback to employee's default shift
        if not shift and employee.shift:
            shift = employee.shift
        
        # Return shift info
        if shift:
            return {
                "id": shift.id,
                "name": shift.name,
                "type": shift_type,
                "start_time": shift.start_time,
                "end_time": shift.end_time,
                "grace_period_minutes": shift.grace_period_minutes,
            }
        
        # Fallback to department default settings
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


class WorkersDepartmentPolicy(UnifiedDepartmentPolicy):
    """Workers department policy - same as unified policy"""
    pass


class DoctorsDepartmentPolicy(AttendancePolicy):
    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return self.calculate_late_minutes(db, employee, check_in_time) > 0

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        if not employee.department:
            return 0
        
        # Use department's new shift settings first, fall back to old ones
        late_start = getattr(employee.department, 'late_start_time', employee.department.half_shift_start_time)
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
        # For doctors: full shift is double half shift, so use 2 * half shift hours as full shift
        half_shift_hours = getattr(employee.department, 'shift_hours', employee.department.half_shift_hours) or 7
        full_shift_hours = half_shift_hours * 2
        
        if working_hours > full_shift_hours:
            return round(working_hours - full_shift_hours, 2)
        return 0.0
    
    def calculate_shift_deficit_hours(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> float:
        if not employee.department:
            return 0.0
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        # Minimum is half shift
        half_shift_hours = getattr(employee.department, 'shift_hours', employee.department.half_shift_hours) or 7
        
        if working_hours < half_shift_hours:
            return round(half_shift_hours - working_hours, 2)
        return 0.0
    
    def get_shift_type(self, employee: Employee, check_in_time: datetime, check_out_time: datetime) -> str:
        if not employee.department:
            return "half_shift"
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        half_shift_hours = getattr(employee.department, 'shift_hours', employee.department.half_shift_hours) or 7
        full_shift_hours = half_shift_hours * 2
        
        if working_hours >= full_shift_hours:
            return "full_shift"
        elif working_hours >= half_shift_hours:
            return "half_shift"
        return "incomplete"

    def supports_shift_system(self) -> bool:
        return True

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        return False

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        if not employee.department:
            return None
        
        # Use new settings first, fall back to old ones
        return {
            "shift_start": getattr(employee.department, 'shift_start_time', employee.department.half_shift_start_time),
            "shift_end": getattr(employee.department, 'shift_end_time', employee.department.half_shift_end_time),
            "shift_hours": getattr(employee.department, 'shift_hours', employee.department.half_shift_hours),
            "late_start": getattr(employee.department, 'late_start_time', employee.department.half_shift_start_time),
            "overtime_start": getattr(employee.department, 'overtime_start_time', employee.department.overtime_start_time),
            "grace_period_minutes": employee.department.grace_period_minutes,
        }


class AttendancePolicyFactory:
    _policies = {
        "default": DefaultAttendancePolicy,
        "leather_department": LeatherDepartmentPolicy,
        "reception_department": ReceptionDepartmentPolicy,
        "doctors_department": DoctorsDepartmentPolicy,
        "workers_department": WorkersDepartmentPolicy,
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
