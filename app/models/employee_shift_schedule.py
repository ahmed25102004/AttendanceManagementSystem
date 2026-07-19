from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EmployeeShiftSchedule(Base):
    __tablename__ = "employee_shift_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "monday", "tuesday", etc.
    shift_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "morning", "evening", "half", "full"
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"), nullable=True)

    employee = relationship("Employee", back_populates="shift_schedules")
    shift = relationship("Shift")
