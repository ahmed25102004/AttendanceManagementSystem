from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    employee_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    face_images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    face_descriptor: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    face_registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    face_verification_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time", nullable=False)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"), nullable=True)
    weekly_rest_day: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "friday", "saturday"
    annual_leave_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sick_leave_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('branch_id', 'employee_code', name='uq_branch_employee_code'),
    )

    branch = relationship("Branch", back_populates="employees")
    department = relationship("Department", back_populates="employees")
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    attendance_logs = relationship("AttendanceLog", back_populates="employee", cascade="all, delete-orphan")
    user = relationship("User", back_populates="employee", uselist=False)
    shift = relationship("Shift", back_populates="employees")
    shift_schedules = relationship("EmployeeShiftSchedule", back_populates="employee", cascade="all, delete-orphan")
