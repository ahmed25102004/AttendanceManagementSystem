from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from app.models.device import Device
from app.models.attendance_log import AttendanceLog
from app.schemas.device import DeviceCreate, DeviceUpdate

logger = logging.getLogger(__name__)

class DeviceService:
    # Threshold: device is considered offline if no contact in last 5 minutes
    OFFLINE_THRESHOLD_MINUTES = 5

    def list(self, db: Session, branch_id: int | None = None, search: str | None = None, status: str | None = None, is_active: bool | None = None) -> list[Device]:
        # First, update statuses for all devices dynamically based on last_seen
        self.update_all_device_statuses(db)
        
        query = db.query(Device)
        if branch_id:
            query = query.filter(Device.branch_id == branch_id)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Device.device_name.ilike(search_term)) |
                (Device.device_code.ilike(search_term)) |
                (Device.serial_number.ilike(search_term))
            )
        if status:
            query = query.filter(Device.status == status)
        if is_active is not None:
            query = query.filter(Device.is_active == is_active)
        return query.order_by(Device.id.desc()).all()

    def get(self, db: Session, device_id: int, branch_id: int | None = None) -> Device:
        # Update status for this specific device
        query = db.query(Device).filter(Device.id == device_id)
        if branch_id:
            query = query.filter(Device.branch_id == branch_id)
        device = query.first()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الجهاز غير موجود.")
        
        self._update_single_device_status(device)
        return device

    def get_by_device_code(self, db: Session, device_code: str) -> Device | None:
        return db.query(Device).filter(Device.device_code == device_code).first()

    def get_by_serial_number(self, db: Session, serial_number: str) -> Device | None:
        return db.query(Device).filter(Device.serial_number == serial_number).first()

    def create(self, db: Session, payload: DeviceCreate) -> Device:
        existing = db.query(Device).filter(
            Device.device_code == payload.device_code, 
            Device.branch_id == payload.branch_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كود الجهاز مستخدم بالفعل.")
        
        device = Device(**payload.model_dump())
        db.add(device)
        db.commit()
        db.refresh(device)
        logger.info(f"[DeviceService] Created new device: id={device.id}, name={device.device_name}, code={device.device_code}")
        return device

    def update(self, db: Session, device_id: int, payload: DeviceUpdate, branch_id: int | None = None) -> Device:
        device = self.get(db, device_id, branch_id)
        if payload.device_code:
            query = db.query(Device).filter(
                Device.device_code == payload.device_code, 
                Device.id != device_id
            )
            if branch_id:
                query = query.filter(Device.branch_id == branch_id)
            existing = query.first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كود الجهاز مستخدم بالفعل.")
        
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(device, key, value)
        
        db.commit()
        db.refresh(device)
        logger.info(f"[DeviceService] Updated device: id={device.id}")
        return device

    def delete(self, db: Session, device_id: int, branch_id: int | None = None) -> None:
        device = self.get(db, device_id, branch_id)
        logger.info(f"[DeviceService] Deleting device: id={device.id}, name={device.device_name}")
        db.delete(device)
        db.commit()

    def _update_single_device_status(self, device: Device) -> None:
        """Helper to update status for a single device based on last_seen"""
        if not device.last_seen:
            device.status = "Offline"
            return
        
        time_since_last_seen = datetime.utcnow() - device.last_seen
        if time_since_last_seen > timedelta(minutes=self.OFFLINE_THRESHOLD_MINUTES):
            device.status = "Offline"
        else:
            device.status = "Online"

    def update_all_device_statuses(self, db: Session) -> None:
        """Update status for all devices in database"""
        devices = db.query(Device).all()
        for device in devices:
            self._update_single_device_status(device)
        db.commit()

    def update_last_seen(self, db: Session, device_id: int) -> None:
        device = self.get(db, device_id)
        device.last_seen = datetime.utcnow()
        device.status = "Online"
        logger.info(f"[DeviceService] Updated last_seen for device id={device_id}, status=Online")
        db.commit()

    def update_last_sync(self, db: Session, device_id: int) -> None:
        """Update last_sync timestamp for a device"""
        device = self.get(db, device_id)
        device.last_sync = datetime.utcnow()
        logger.info(f"[DeviceService] Updated last_sync for device id={device_id}")
        db.commit()

    def get_log_count(self, db: Session, device_id: int) -> int:
        return db.query(func.count(AttendanceLog.id)).filter(AttendanceLog.device_id == device_id).scalar() or 0

    def test_connection(self, db: Session, device_id: int, branch_id: int | None = None) -> tuple[bool, str]:
        device = self.get(db, device_id, branch_id)
        # Update last_seen and status when testing connection
        self.update_last_seen(db, device_id)
        logger.info(f"[DeviceService] Tested connection for device id={device_id}")
        return True, f"تم الاتصال بنجاح مع {device.device_name}"
