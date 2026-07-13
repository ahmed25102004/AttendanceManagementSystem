from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    employee_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    check_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    attendance_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verify_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="ZKTeco", nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    record_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="attendance_logs")
    branch = relationship("Branch")
    device = relationship("Device", back_populates="attendance_logs")
