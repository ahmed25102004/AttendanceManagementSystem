from datetime import date, datetime
from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Date, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveType(str, Enum):
    SICK = "sick"
    ANNUAL = "annual"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"


class Leave(Base):
    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    type: Mapped[LeaveType] = mapped_column(SQLEnum(LeaveType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LeaveStatus] = mapped_column(SQLEnum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    employee = relationship("Employee", back_populates="leaves")
