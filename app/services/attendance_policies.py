from abc import ABC, abstractmethod
from datetime import datetime, date, time
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


class ReceptionDepartmentPolicy(AttendancePolicy):
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        return self.calculate_late_minutes(db, employee, check_in_time) > 0

    def calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        shift_info = self.get_shift_for_day(db, employee, check_in_time.date())
        if not shift_info:
            return 0
        shift_start = datetime.combine(check_in_time.date(), shift_info["start_time"])
        grace_period = shift_info.get("grace_period_minutes", 15)
        late_threshold = shift_start.timestamp() + (grace_period * 60)
        if check_in_time.timestamp() > late_threshold:
            return int((check_in_time.timestamp() - shift_start.timestamp()) / 60)
        return 0

    def calculate_working_hours(self, check_in_time: datetime, check_out_time: datetime) -> float:
        seconds = max((check_out_time - check_in_time).total_seconds(), 0)
        return round(seconds / 3600, 2)

    def supports_shift_system(self) -> bool:
        return True

    def is_rest_day(self, db: Session, employee: Employee, check_date: date) -> bool:
        if not employee.weekly_rest_day:
            return False
        check_day = self.DAY_NAMES[check_date.weekday()]
        return check_day.lower() == employee.weekly_rest_day.lower()

    def get_shift_for_day(self, db: Session, employee: Employee, check_date: date) -> Optional[Dict[str, Any]]:
        check_day = self.DAY_NAMES[check_date.weekday()]
        schedule = db.query(EmployeeShiftSchedule).filter(
            EmployeeShiftSchedule.employee_id == employee.id,
            EmployeeShiftSchedule.day_of_week == check_day.lower()
        ).first()
        if not schedule:
            if employee.shift:
                return {
                    "id": employee.shift.id,
                    "name": employee.shift.name,
                    "start_time": employee.shift.start_time,
                    "end_time": employee.shift.end_time,
                    "grace_period_minutes": employee.shift.grace_period_minutes,
                }
            return None
        shift: Optional[Shift] = None
        if schedule.shift_id:
            shift = db.query(Shift).filter(Shift.id == schedule.shift_id).first()
        if not shift:
            # Fallback to default shifts by name or employee's shift
            if schedule.shift_type in ["morning", "صباحي"]:
                shift = db.query(Shift).filter(Shift.name == "صباحي").first()
            elif schedule.shift_type in ["evening", "مسائي"]:
                shift = db.query(Shift).filter(Shift.name == "مسائي").first()
            elif schedule.shift_type in ["half", "نصف", "half_shift"]:
                shift = db.query(Shift).filter(Shift.name.in_(["نصف شيفت", "Half Shift"])).first()
            elif schedule.shift_type in ["full", "كامل", "full_shift"]:
                shift = db.query(Shift).filter(Shift.name.in_(["شيفت كامل", "Full Shift"])).first()
            if not shift and employee.shift:
                shift = employee.shift
        if shift:
            return {
                "id": shift.id,
                "name": shift.name,
                "type": schedule.shift_type,
                "start_time": shift.start_time,
                "end_time": shift.end_time,
                "grace_period_minutes": shift.grace_period_minutes,
            }
        return None


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
            return "نصف شيفت"
        
        working_hours = self.calculate_working_hours(check_in_time, check_out_time)
        half_shift_hours = getattr(employee.department, 'shift_hours', employee.department.half_shift_hours) or 7
        full_shift_hours = half_shift_hours * 2
        
        if working_hours >= full_shift_hours:
            return "شفت كامل"
        elif working_hours >= half_shift_hours:
            return "نصف شيفت"
        return "نقص في الشفت"

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
