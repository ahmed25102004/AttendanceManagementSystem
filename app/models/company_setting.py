from datetime import time

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompanySetting(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True, unique=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    work_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0), nullable=False)
    work_end_time: Mapped[time] = mapped_column(Time, default=time(17, 0), nullable=False)
    weekend_days: Mapped[str] = mapped_column(String(50), default="Saturday,Sunday", nullable=False)
    late_grace_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    workplace_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    workplace_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    workplace_radius_meters: Mapped[int] = mapped_column(Integer, default=150, nullable=False)
    allowed_ip_ranges: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    enforce_geofence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enforce_ip_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    face_match_threshold: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    check_in_open_time: Mapped[time] = mapped_column(Time, default=time(8, 0), nullable=False)
    check_in_close_time: Mapped[time] = mapped_column(Time, default=time(11, 0), nullable=False)
    check_out_open_time: Mapped[time] = mapped_column(Time, default=time(16, 0), nullable=False)
    check_out_close_time: Mapped[time] = mapped_column(Time, default=time(22, 0), nullable=False)
    auto_backup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_backup_time: Mapped[time] = mapped_column(Time, default=time(2, 0), nullable=False)
    auto_backup_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    zkteco_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    zkteco_ip: Mapped[str] = mapped_column(String(50), default="192.168.1.201", nullable=False)
    zkteco_port: Mapped[int] = mapped_column(Integer, default=4370, nullable=False)
    zkteco_password: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    zkteco_auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    zkteco_auto_sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    branch = relationship("Branch")
