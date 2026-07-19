
from datetime import date, datetime, timedelta
from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.department import Department
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord
from app.services.reception_service import ReceptionService


class DepartmentService:
    def __init__(self) -> None:
        self.reception_service = ReceptionService()

    def _employee_full_name(self, employee: Employee) -> str:
        return " ".join(part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip())

    def list(self, db: Session, branch_id: int | None = None) -> list[Department]:
        query = db.query(Department).order_by(Department.id.desc())
        if branch_id:
            query = query.filter(Department.branch_id == branch_id)
        return query.all()

    def get(self, db: Session, department_id: int, branch_id: int | None = None) -> Department:
        query = db.query(Department).filter(Department.id == department_id)
        if branch_id:
            query = query.filter(Department.branch_id == branch_id)
        department = query.first()
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="القسم غير موجود.")
        return department

    def get_stats(self, db: Session, department_id: int, branch_id: int | None = None) -> dict:
        # Check department exists
        department = self.get(db, department_id, branch_id)
        if self.reception_service.is_reception_department(department) or self.reception_service.is_leather_department(department):
            reception_stats = self.reception_service.get_department_today_stats(db, department_id)
            return {
                "id": department_id,
                "name": department.name,
                "description": department.description,
                "attendance_policy": department.attendance_policy,
                "is_active": department.is_active,
                # New fields
                "shift_start_time": getattr(department, "shift_start_time", department.half_shift_start_time),
                "shift_end_time": getattr(department, "shift_end_time", department.half_shift_end_time),
                "shift_hours": getattr(department, "shift_hours", department.half_shift_hours),
                "late_start_time": getattr(department, "late_start_time", department.half_shift_start_time),
                "attendance_end_time": getattr(department, "attendance_end_time", None),
                "overtime_start_time": department.overtime_start_time,
                "evening_shift_start_time": getattr(department, "evening_shift_start_time", None),
                "evening_shift_end_time": getattr(department, "evening_shift_end_time", None),
                "evening_shift_hours": getattr(department, "evening_shift_hours", None),
                # Old fields (backward compatibility)
                "half_shift_start_time": department.half_shift_start_time,
                "half_shift_end_time": department.half_shift_end_time,
                "half_shift_hours": department.half_shift_hours,
                "full_shift_start_time": department.full_shift_start_time,
                "full_shift_end_time": department.full_shift_end_time,
                "full_shift_hours": department.full_shift_hours,
                "grace_period_minutes": department.grace_period_minutes,
                "total_employees": len(reception_stats["employees"]),
                "attendance_today": reception_stats["attendance_today"],
                "employees": reception_stats["employees"],
                "latest_attendance": reception_stats["latest_attendance"],
            }

        today = date.today()

        total_employees = db.query(func.count(Employee.id)).filter(
            Employee.department_id == department_id, Employee.branch_id == branch_id, Employee.is_active.is_(True)
        ).scalar()

        # Get today's attendance for department
        today_attendance = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.employee.has(department_id=department_id, branch_id=branch_id),
            AttendanceRecord.attendance_date == today
        ).scalar()

        # Get employees in department with their attendance today
        employees_in_department = db.query(Employee).options(
            joinedload(Employee.attendance_records)
        ).filter(
            Employee.department_id == department_id, Employee.branch_id == branch_id, Employee.is_active.is_(True)
        ).all()

        # Get latest attendance records for department employees
        latest_attendance = db.query(AttendanceRecord).options(
            joinedload(AttendanceRecord.employee)
        ).filter(
            AttendanceRecord.employee.has(department_id=department_id, branch_id=branch_id)
        ).order_by(AttendanceRecord.check_in_time.desc()).limit(10).all()

        return {
            "id": department_id,
            "name": department.name,
            "description": department.description,
            "attendance_policy": department.attendance_policy,
            "is_active": department.is_active,
            # New fields
            "shift_start_time": getattr(department, "shift_start_time", department.half_shift_start_time),
            "shift_end_time": getattr(department, "shift_end_time", department.half_shift_end_time),
            "shift_hours": getattr(department, "shift_hours", department.half_shift_hours),
            "late_start_time": getattr(department, "late_start_time", department.half_shift_start_time),
            "attendance_end_time": getattr(department, "attendance_end_time", None),
            "overtime_start_time": department.overtime_start_time,
            "evening_shift_start_time": getattr(department, "evening_shift_start_time", None),
            "evening_shift_end_time": getattr(department, "evening_shift_end_time", None),
            "evening_shift_hours": getattr(department, "evening_shift_hours", None),
            # Old fields (backward compatibility)
            "half_shift_start_time": department.half_shift_start_time,
            "half_shift_end_time": department.half_shift_end_time,
            "half_shift_hours": department.half_shift_hours,
            "full_shift_start_time": department.full_shift_start_time,
            "full_shift_end_time": department.full_shift_end_time,
            "full_shift_hours": department.full_shift_hours,
            "grace_period_minutes": department.grace_period_minutes,
            "total_employees": total_employees,
            "attendance_today": today_attendance,
            "employees": [
                {
                    "id": e.id,
                    "full_name": self._employee_full_name(e),
                    "employee_code": e.employee_code,
                    "attendance_today": any(
                        ar.attendance_date == today for ar in e.attendance_records
                    )
                }
                for e in employees_in_department
            ],
            "latest_attendance": [
                {
                    "id": ar.id,
                    "employee_id": ar.employee_id,
                    "employee_name": self._employee_full_name(ar.employee) if ar.employee else None,
                    "attendance_date": ar.attendance_date,
                    "check_in_time": ar.check_in_time,
                    "check_out_time": ar.check_out_time,
                    "is_late": ar.is_late,
                    "working_hours": ar.working_hours
                }
                for ar in latest_attendance
            ]
        }
