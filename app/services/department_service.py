from datetime import date, datetime, timedelta
from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.department import Department
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord
from app.services.reception_service import ReceptionService
from app.services.workers_service import WorkersService
from app.services.call_center_service import CallCenterService


class DepartmentService:
    def __init__(self) -> None:
        self.reception_service = ReceptionService()
        self.workers_service = WorkersService()
        self.call_center_service = CallCenterService()

    def _employee_full_name(self, employee: Employee) -> str:
        return " ".join(part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip())

    def list(self, db: Session, branch_id: int | None = None) -> list[Department]:
        query = db.query(Department).order_by(Department.id.desc())
        if branch_id:
            query = query.filter(Department.branch_id == branch_id)
        return query.all()

    def get(self, db: Session, department_id: int, branch_id: int | None = None) -> Department:
        query = db.query(Department).filter(Department.id == department_id)
        department = query.first()
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="القسم غير موجود.")
        return department

    def _is_workers_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "workers_department")

    def _is_call_center_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "call_center_department")

    def _is_reception_or_leather_department(self, department: Department | None) -> bool:
        return bool(department and (department.attendance_policy in {"reception_department", "leather_department", "doctors_department", "default"}))

    def _is_unified_department(self, department: Department | None) -> bool:
        return True

    def get_stats(self, db: Session, department_id: int, branch_id: int | None = None) -> dict:
        # Check department exists
        department = self.get(db, department_id, branch_id)
        effective_branch_id = department.branch_id or branch_id

        if self._is_unified_department(department):
            # Route to correct service based on policy
            if self._is_call_center_department(department) or self._is_workers_department(department):
                today_stats = self.call_center_service.get_department_today_stats(db, department_id, effective_branch_id)
            else:
                today_stats = self.reception_service.get_department_today_stats(db, department_id, effective_branch_id)
            return {
                "id": department_id,
                "name": department.name,
                "description": department.description,
                "attendance_policy": department.attendance_policy,
                "is_active": department.is_active,
                "shift_start_time": department.shift_start_time,
                "shift_end_time": department.shift_end_time,
                "shift_hours": department.shift_hours,
                "late_start_time": department.late_start_time,
                "attendance_end_time": department.attendance_end_time,
                "overtime_enabled": department.overtime_enabled,
                "overtime_start_time": department.overtime_start_time,
                "evening_shift_start_time": department.evening_shift_start_time,
                "evening_shift_end_time": department.evening_shift_end_time,
                "evening_shift_hours": department.evening_shift_hours,
                "evening_shift_late_start_time": department.evening_shift_late_start_time,
                "total_employees": len(today_stats["employees"]),
                "attendance_today": today_stats["attendance_today"],
                "employees": today_stats["employees"],
                "latest_attendance": today_stats["latest_attendance"],
            }

        today = date.today()

        total_employees = db.query(func.count(Employee.id)).filter(
            Employee.department_id == department_id, Employee.is_active.is_(True)
        ).scalar()

        # Get today's attendance for department
        today_attendance = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.employee.has(department_id=department_id),
            AttendanceRecord.attendance_date == today
        ).scalar()

        # Get employees in department with their attendance today
        employees_in_department = db.query(Employee).options(
            joinedload(Employee.attendance_records)
        ).filter(
            Employee.department_id == department_id, Employee.is_active.is_(True)
        ).all()

        # Get latest attendance records for department employees
        latest_attendance = db.query(AttendanceRecord).options(
            joinedload(AttendanceRecord.employee)
        ).filter(
            AttendanceRecord.employee.has(department_id=department_id)
        ).order_by(AttendanceRecord.check_in_time.desc()).limit(10).all()

        return {
            "id": department_id,
            "name": department.name,
            "description": department.description,
            "attendance_policy": department.attendance_policy,
            "is_active": department.is_active,
            "shift_start_time": department.shift_start_time,
            "shift_end_time": department.shift_end_time,
            "shift_hours": department.shift_hours,
            "late_start_time": department.late_start_time,
            "attendance_end_time": department.attendance_end_time,
            "overtime_enabled": department.overtime_enabled,
            "overtime_start_time": department.overtime_start_time,
            "evening_shift_start_time": department.evening_shift_start_time,
            "evening_shift_end_time": department.evening_shift_end_time,
            "evening_shift_hours": department.evening_shift_hours,
            "evening_shift_late_start_time": department.evening_shift_late_start_time,
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
