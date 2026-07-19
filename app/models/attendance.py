from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    working_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shift_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    shift_units: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shift_deficit_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="present", nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    verification_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_rest_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    worked_on_rest_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee = relationship("Employee", back_populates="attendance_records")
