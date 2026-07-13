from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.attendance_log import AttendanceLog
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceService:
    def list(self, db: Session, branch_id: int | None = None, search: str | None = None, status: str | None = None, is_active: bool | None = None) -> list[Device]:
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

    def get(self, db: Session, device_id: int) -> Device:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الجهاز غير موجود.")
        return device

    def get_by_device_code(self, db: Session, device_code: str) -> Device | None:
        return db.query(Device).filter(Device.device_code == device_code).first()

    def get_by_serial_number(self, db: Session, serial_number: str) -> Device | None:
        return db.query(Device).filter(Device.serial_number == serial_number).first()

    def create(self, db: Session, payload: DeviceCreate) -> Device:
        existing = db.query(Device).filter(Device.device_code == payload.device_code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كود الجهاز مستخدم بالفعل.")
        
        device = Device(**payload.model_dump())
        db.add(device)
        db.commit()
        db.refresh(device)
        return device

    def update(self, db: Session, device_id: int, payload: DeviceUpdate) -> Device:
        device = self.get(db, device_id)
        if payload.device_code:
            existing = db.query(Device).filter(
                Device.device_code == payload.device_code, 
                Device.id != device_id
            ).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="كود الجهاز مستخدم بالفعل.")
        
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(device, key, value)
        
        db.commit()
        db.refresh(device)
        return device

    def delete(self, db: Session, device_id: int) -> None:
        device = self.get(db, device_id)
        db.delete(device)
        db.commit()

    def update_last_seen(self, db: Session, device_id: int) -> None:
        device = self.get(db, device_id)
        device.last_seen = datetime.utcnow()
        device.status = "Online"
        db.commit()

    def get_log_count(self, db: Session, device_id: int) -> int:
        return db.query(func.count(AttendanceLog.id)).filter(AttendanceLog.device_id == device_id).scalar() or 0

    def test_connection(self, db: Session, device_id: int) -> tuple[bool, str]:
        device = self.get(db, device_id)
        # For now, return mock success. Later integrate with zkteco library if needed
        return True, f"تم الاتصال بنجاح مع {device.device_name}"
