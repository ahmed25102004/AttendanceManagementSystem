from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.security import security_manager
from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_shift_schedule import EmployeeShiftSchedule
from app.models.shift import Shift
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate, 
    EmployeeResponse, 
    EmployeeUpdate, 
    EmployeeProfileResponse, 
    AttendanceLogEntry,
    EmployeeShiftScheduleEntry,
    EmployeeShiftScheduleResponse,
    EmployeeShiftScheduleUpdate,
    EmployeeStatsResponse
)
from app.services.biometric_service import FaceRecognitionMatcher
from app.services.reception_service import ReceptionService


class EmployeeService:
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def __init__(self) -> None:
        self.face_matcher = FaceRecognitionMatcher()
        self.reception_service = ReceptionService()

    def _normalize_role(self, role: str | None) -> str:
        normalized_role = (role or "employee").strip().lower()
        if normalized_role not in {"admin", "employee"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الدور غير صالح. يسمح فقط بـ admin أو employee.")
        return normalized_role

    def _portal_username(self, employee_id: int) -> str:
        return f"emp_{employee_id}"

    def _employee_email(self, employee_id: int) -> str:
        return f"emp_{employee_id}@employee.local"

    def _normalize_full_name(self, full_name: str) -> str:
        normalized_name = " ".join(full_name.split()).strip()
        if len(normalized_name) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم الموظف غير صالح.")
        return normalized_name

    def _compose_full_name(self, first_name: str, last_name: str | None) -> str:
        return " ".join(part.strip() for part in [first_name, last_name or ""] if part and part.strip())

    def _normalize_weekly_rest_day(self, weekly_rest_day: str | None) -> str | None:
        if weekly_rest_day is None:
            return None
        normalized = weekly_rest_day.strip().lower()
        if not normalized:
            return None
        if normalized not in self.DAY_NAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يوم الإجازة الأسبوعية غير صالح.",
            )
        return normalized

    def _employee_query(self, db: Session):
        return db.query(Employee).options(
            joinedload(Employee.department),
            joinedload(Employee.shift),
            joinedload(Employee.shift_schedules).joinedload(EmployeeShiftSchedule.shift),
            joinedload(Employee.user),
        )

    def _schedule_entry_to_response(self, entry: EmployeeShiftSchedule) -> EmployeeShiftScheduleEntry:
        return EmployeeShiftScheduleEntry(
            day_of_week=entry.day_of_week,
            shift_type=entry.shift_type,
            shift_id=entry.shift_id,
            shift_name=entry.shift.name if entry.shift else None,
            start_time=entry.shift.start_time.strftime("%H:%M") if entry.shift and entry.shift.start_time else None,
            end_time=entry.shift.end_time.strftime("%H:%M") if entry.shift and entry.shift.end_time else None,
            grace_period_minutes=entry.shift.grace_period_minutes if entry.shift else None,
        )

    def _validate_shift(self, db: Session, shift_id: int | None) -> Shift | None:
        if shift_id is None:
            return None
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الوردية غير موجودة.")
        return shift



    def _sync_employee_user(
        self,
        db: Session,
        employee: Employee,
        role: str = "employee",
    ) -> None:
        normalized_role = self._normalize_role(role)
        full_name = self._compose_full_name(employee.first_name, employee.last_name)
        
        # Get existing user first
        user = db.query(User).filter(User.employee_id == employee.id).first()
        
        # Generate username automatically
        username = self._portal_username(employee.id)
            
        conflicting_user = (
            db.query(User)
            .filter(User.username == username, or_(User.employee_id.is_(None), User.employee_id != employee.id))
            .first()
        )
        if conflicting_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تعذر إنشاء حساب دخول الموظف بسبب تعارض في اسم المستخدم.",
            )

        if not user:
            password = f"emp_{employee.id}@123"
            user = User(
                username=username,
                password_hash=security_manager.hash_password(password),
                full_name=full_name,
                role=normalized_role,
                is_active=employee.is_active,
                employee_id=employee.id,
            )
            db.add(user)
            return

        user.username = username
        user.full_name = full_name
        user.is_active = employee.is_active
        user.role = normalized_role

    def _to_response(self, employee: Employee) -> EmployeeResponse:
        # Fallback to employee.id as string if employee_code is None or empty
        employee_code = employee.employee_code
        if not employee_code or employee_code.strip() == "":
            employee_code = str(employee.id)
            # Also update the database so we don't have to do this again
            employee.employee_code = employee_code
        
        return EmployeeResponse(
            id=employee.id,
            full_name=self._compose_full_name(employee.first_name, employee.last_name),
            role=employee.user.role if getattr(employee, 'user', None) else "employee",
            employee_code=employee_code,
            first_name=employee.first_name,
            last_name=employee.last_name,
            phone=employee.phone,
            address=employee.address,
            job_title=employee.job_title,
            hire_date=employee.hire_date,
            department_id=employee.department_id,
            branch_id=employee.branch_id,
            employment_type=employee.employment_type,
            shift_id=employee.shift_id,
            weekly_rest_day=employee.weekly_rest_day,
            shift_name=employee.shift.name if employee.shift else None,
            is_active=employee.is_active,
        )

    def list(self, db: Session, search: str | None = None, branch_id: int | None = None, department_id: int | None = None, is_active: bool | None = None, employment_type: str | None = None) -> list[EmployeeResponse]:
        query = self._employee_query(db)
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        if employment_type:
            query = query.filter(Employee.employment_type == employment_type)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_term),
                    Employee.last_name.ilike(search_term),
                    Employee.job_title.ilike(search_term),
                    Employee.employee_code.ilike(search_term),
                )
            )
        employees = query.order_by(Employee.id.desc()).all()
        responses = [self._to_response(employee) for employee in employees]
        # Commit any employee_code updates to the database
        db.commit()
        return responses

    def create(self, db: Session, payload: EmployeeCreate, branch_id: int | None = None) -> EmployeeResponse:
        # Check if employee_code already exists in the same branch
        final_branch_id = payload.branch_id or branch_id
        query = db.query(Employee).filter(Employee.employee_code == payload.employee_code)
        if final_branch_id:
            query = query.filter(Employee.branch_id == final_branch_id)
        existing_employee = query.first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كود الموظف مستخدم بالفعل في هذا الفرع."
            )
        
        employee = Employee(
            first_name=self._normalize_full_name(payload.full_name),
            last_name="",
            employee_code=payload.employee_code,
            email="temp@temp.local",  # temp, will be updated after flush
            phone=payload.phone,
            address=payload.address,
            job_title=payload.job_title,
            hire_date=payload.hire_date,
            is_active=True,
            department_id=payload.department_id,
            employment_type=payload.employment_type,
            branch_id=final_branch_id,
            shift_id=payload.shift_id,
            weekly_rest_day=self._normalize_weekly_rest_day(payload.weekly_rest_day),
        )
        self._validate_shift(db, payload.shift_id)
        db.add(employee)
        db.flush()
        # Now we have employee.id, update email
        employee.email = self._employee_email(employee.id)
        self._sync_employee_user(
            db,
            employee,
            role=payload.role,
        )
        db.commit()
        db.refresh(employee)
        employee = self._employee_query(db).filter(Employee.id == employee.id).first()
        return self._to_response(employee)

    def update(self, db: Session, employee_id: int, payload: EmployeeUpdate, branch_id: int | None = None) -> EmployeeResponse:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
        
        # Check if employee_code is being changed and if it's already used in the same branch
        final_branch_id = payload.branch_id or branch_id or employee.branch_id
        if payload.employee_code and payload.employee_code != employee.employee_code:
            query = db.query(Employee).filter(Employee.employee_code == payload.employee_code, Employee.id != employee_id)
            if final_branch_id:
                query = query.filter(Employee.branch_id == final_branch_id)
            existing_employee = query.first()
            if existing_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="كود الموظف مستخدم بالفعل في هذا الفرع."
                )

        employee.first_name = self._normalize_full_name(payload.full_name)
        employee.last_name = ""
        employee.employee_code = payload.employee_code
        employee.phone = payload.phone
        employee.address = payload.address
        employee.job_title = payload.job_title
        employee.hire_date = payload.hire_date
        employee.department_id = payload.department_id
        employee.branch_id = payload.branch_id or branch_id
        employee.employment_type = payload.employment_type
        employee.shift_id = payload.shift_id
        employee.weekly_rest_day = self._normalize_weekly_rest_day(payload.weekly_rest_day)
        self._validate_shift(db, payload.shift_id)

        self._sync_employee_user(
            db,
            employee,
            role=payload.role,
        )
        db.commit()
        db.refresh(employee)
        employee = self._employee_query(db).filter(Employee.id == employee.id).first()
        return self._to_response(employee)

    def delete(self, db: Session, employee_id: int, branch_id: int | None = None) -> None:
        query = db.query(Employee).filter(Employee.id == employee_id)
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        employee = query.first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
        try:
            db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == employee.id).delete(synchronize_session=False)
            linked_user = db.query(User).filter(User.employee_id == employee.id).first()
            if linked_user:
                db.delete(linked_user)
            db.delete(employee)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن حذف الموظف لوجود سجلات حضور مرتبطة به.",
            ) from exc

    def get_profile(self, db: Session, employee_id: int, branch_id: int | None = None) -> EmployeeProfileResponse:
        query = self._employee_query(db).options(
            joinedload(Employee.branch),
        ).filter(Employee.id == employee_id)
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        employee = query.first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
        
        return EmployeeProfileResponse(
            id=employee.id,
            full_name=self._compose_full_name(employee.first_name, employee.last_name),
            role=employee.user.role if getattr(employee, 'user', None) else "employee",
            employee_code=employee.employee_code,
            first_name=employee.first_name,
            last_name=employee.last_name,
            phone=employee.phone,
            address=employee.address,
            job_title=employee.job_title,
            hire_date=employee.hire_date,
            department_id=employee.department_id,
            branch_id=employee.branch_id,
            employment_type=employee.employment_type,
            shift_id=employee.shift_id,
            weekly_rest_day=employee.weekly_rest_day,
            branch_name=employee.branch.name if employee.branch else None,
            department_name=employee.department.name if employee.department else None,
            shift_name=employee.shift.name if employee.shift else None,
            face_enrolled=bool(employee.face_descriptor is not None),
            is_active=employee.is_active,
        )

    def get_shift_schedule(
        self,
        db: Session,
        employee_id: int,
        branch_id: int | None = None,
    ) -> EmployeeShiftScheduleResponse:
        query = self._employee_query(db).filter(Employee.id == employee_id)
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        employee = query.first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")

        schedules = sorted(
            employee.shift_schedules,
            key=lambda item: self.DAY_NAMES.index(item.day_of_week.strip().lower()),
        )
        return EmployeeShiftScheduleResponse(
            employee_id=employee.id,
            shift_id=employee.shift_id,
            shift_name=employee.shift.name if employee.shift else None,
            weekly_rest_day=employee.weekly_rest_day,
            schedules=[self._schedule_entry_to_response(entry) for entry in schedules],
        )

    def update_shift_schedule(
        self,
        db: Session,
        employee_id: int,
        payload: EmployeeShiftScheduleUpdate,
        branch_id: int | None = None,
    ) -> EmployeeShiftScheduleResponse:
        query = self._employee_query(db).filter(Employee.id == employee_id)
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        employee = query.first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")

        self._validate_shift(db, payload.shift_id)
        employee.shift_id = payload.shift_id
        employee.weekly_rest_day = self._normalize_weekly_rest_day(payload.weekly_rest_day)

        existing_by_day = {item.day_of_week.strip().lower(): item for item in employee.shift_schedules}
        incoming_days: set[str] = set()

        for item in payload.schedules:
            normalized_day = item.day_of_week.strip().lower()
            if normalized_day not in self.DAY_NAMES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اليوم المحدد في جدول الشيفت غير صالح.")

            self._validate_shift(db, item.shift_id)
            incoming_days.add(normalized_day)
            schedule = existing_by_day.get(normalized_day)
            if not schedule:
                schedule = EmployeeShiftSchedule(
                    employee_id=employee.id,
                    day_of_week=normalized_day,
                )
                db.add(schedule)
                employee.shift_schedules.append(schedule)

            schedule.shift_type = item.shift_type.strip().lower()
            schedule.shift_id = item.shift_id

        for day_name, schedule in list(existing_by_day.items()):
            if day_name not in incoming_days:
                db.delete(schedule)

        db.commit()
        return self.get_shift_schedule(db, employee_id, branch_id)

    def get_attendance_logs(
        self, 
        db: Session, 
        employee_id: int, 
        start_date: date | None = None, 
        end_date: date | None = None, 
        branch_id: int | None = None
    ) -> List[AttendanceLogEntry]:
        query = db.query(AttendanceLog).options(
            joinedload(AttendanceLog.device),
            joinedload(AttendanceLog.branch)
        ).filter(AttendanceLog.employee_id == employee_id)
        if branch_id:
            query = query.filter(AttendanceLog.branch_id == branch_id)
        if start_date:
            query = query.filter(func.date(AttendanceLog.check_time) >= start_date)
        if end_date:
            query = query.filter(func.date(AttendanceLog.check_time) <= end_date)
        logs = query.order_by(AttendanceLog.check_time.desc()).all()
        return [
            AttendanceLogEntry(
                id=log.id,
                check_time=log.check_time,
                attendance_type=log.attendance_type,
                verify_type=log.verify_type,
                device_name=log.device.device_name if log.device else None,
                branch_name=log.branch.name if log.branch else None
            )
            for log in logs
        ]

    def get_stats(
        self, 
        db: Session, 
        employee_id: int, 
        start_date: date | None = None, 
        end_date: date | None = None, 
        branch_id: int | None = None
    ) -> EmployeeStatsResponse:
        # Set default to last 30 days
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        employee = self._employee_query(db).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
        if branch_id and employee.branch_id != branch_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")

        if self.reception_service.is_reception_department(employee.department) or self.reception_service.is_leather_department(employee.department):
            rows = [
                row
                for row in self.reception_service.build_report_rows(
                    db,
                    employee.department_id,
                    start_date,
                    end_date,
                    branch_id,
                )
                if row.employee_code == employee.employee_code
            ]
            total_hours = sum(row.working_hours for row in rows)
            present_days = len([row for row in rows if row.status in {"present", "present_on_rest_day"}])
            absent_days = len([row for row in rows if row.status == "absent"])
            late_days = len([row for row in rows if row.late_minutes > 0])
            total_days = (end_date - start_date).days + 1
            attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0.0

            return EmployeeStatsResponse(
                total_hours=round(total_hours, 2),
                overtime_hours=0.0,
                attendance_rate=round(attendance_rate, 2),
                present_days=present_days,
                absent_days=absent_days,
                late_days=late_days,
                early_leave_days=0,
            )

        # Get attendance logs
        logs_query = db.query(AttendanceLog).filter(
            AttendanceLog.employee_id == employee_id, func.date(AttendanceLog.check_time) >= start_date, func.date(AttendanceLog.check_time) <= end_date)
        if branch_id:
            logs_query = logs_query.filter(AttendanceLog.branch_id == branch_id)
        
        # Get attendance records (AttendanceRecord) for stats
        records_query = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee_id, AttendanceRecord.attendance_date >= start_date, AttendanceRecord.attendance_date <= end_date
        )
        if branch_id:
            records_query = records_query.join(Employee).filter(Employee.branch_id == branch_id)

        total_records = records_query.all()
        
        total_hours = sum(r.working_hours for r in total_records)
        overtime_hours = 0.0
        present_days = len([r for r in total_records if r.status == "present"])
        absent_days = len([r for r in total_records if r.status == "absent"])
        late_days = len([r for r in total_records if r.is_late])
        early_leave_days = 0
        
        total_days = (end_date - start_date).days + 1
        attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0.0
        
        return EmployeeStatsResponse(
            total_hours=round(total_hours, 2),
            overtime_hours=round(overtime_hours, 2),
            attendance_rate=round(attendance_rate, 2),
            present_days=present_days,
            absent_days=absent_days,
            late_days=late_days,
            early_leave_days=early_leave_days
        )
