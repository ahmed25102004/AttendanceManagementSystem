from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.security import security_manager
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.biometric_service import FaceRecognitionMatcher


class EmployeeService:
    def __init__(self) -> None:
        self.face_matcher = FaceRecognitionMatcher()

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
        return EmployeeResponse(
            id=employee.id,
            full_name=self._compose_full_name(employee.first_name, employee.last_name),
            role=employee.user.role if getattr(employee, 'user', None) else "employee",
            first_name=employee.first_name,
            last_name=employee.last_name,
            phone=employee.phone,
            address=employee.address,
            job_title=employee.job_title,
            hire_date=employee.hire_date,
            department_id=employee.department_id,
        )

    def list(self, db: Session, search: str | None = None) -> list[EmployeeResponse]:
        query = db.query(Employee).options(joinedload(Employee.department))
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_term),
                    Employee.last_name.ilike(search_term),
                    Employee.job_title.ilike(search_term),
                )
            )
        employees = query.order_by(Employee.id.desc()).all()
        return [self._to_response(employee) for employee in employees]

    def create(self, db: Session, payload: EmployeeCreate) -> EmployeeResponse:
        employee = Employee(
            first_name=self._normalize_full_name(payload.full_name),
            last_name="",
            email="temp@temp.local",  # temp, will be updated after flush
            phone=payload.phone,
            address=payload.address,
            job_title=payload.job_title,
            hire_date=payload.hire_date,
            is_active=True,
            department_id=payload.department_id,
            employment_type=payload.employment_type,
        )
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
        employee = (
            db.query(Employee).filter(Employee.id == employee.id).first()
        )
        return self._to_response(employee)

    def update(self, db: Session, employee_id: int, payload: EmployeeUpdate) -> EmployeeResponse:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")

        employee.first_name = self._normalize_full_name(payload.full_name)
        employee.last_name = ""
        employee.phone = payload.phone
        employee.address = payload.address
        employee.job_title = payload.job_title
        employee.hire_date = payload.hire_date
        employee.department_id = payload.department_id
        employee.employment_type = payload.employment_type

        self._sync_employee_user(
            db,
            employee,
            role=payload.role,
        )
        db.commit()
        db.refresh(employee)
        employee = (
            db.query(Employee).filter(Employee.id == employee.id).first()
        )
        return self._to_response(employee)

    def delete(self, db: Session, employee_id: int) -> None:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
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
