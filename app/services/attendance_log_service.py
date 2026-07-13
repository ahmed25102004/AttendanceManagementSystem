from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.models.device import Device


class AttendanceLogService:
    def __init__(self):
        self.logger = __import__('logging').getLogger(__name__)

    def list(self, db: Session, branch_id: int | None = None, device_id: int | None = None, start_date: datetime | None = None, end_date: datetime | None = None, employee_code: str | None = None, attendance_type: str | None = None, verify_type: str | None = None) -> list[AttendanceLog]:
        query = db.query(AttendanceLog)
        if branch_id:
            query = query.filter(AttendanceLog.branch_id == branch_id)
        if device_id:
            query = query.filter(AttendanceLog.device_id == device_id)
        if start_date:
            query = query.filter(AttendanceLog.check_time >= start_date)
        if end_date:
            query = query.filter(AttendanceLog.check_time <= end_date)
        if employee_code:
            query = query.filter(AttendanceLog.employee_code.ilike(f"%{employee_code}%"))
        if attendance_type:
            query = query.filter(AttendanceLog.attendance_type == attendance_type)
        if verify_type:
            query = query.filter(AttendanceLog.verify_type == verify_type)
        return query.order_by(AttendanceLog.check_time.desc()).all()

    def is_duplicate(self, db: Session, device_id: int, employee_code: str, check_time: datetime, record_id: str | None = None) -> bool:
        query = db.query(AttendanceLog).filter(
            AttendanceLog.device_id == device_id,
            AttendanceLog.employee_code == employee_code,
            AttendanceLog.check_time == check_time
        )
        if record_id:
            query = query.filter(AttendanceLog.record_id != record_id)
        return query.first() is not None

    def create(self, db: Session, device: Device, employee_code: str, check_time: datetime, 
               attendance_type: str | None = None, verify_type: str | None = None, 
               raw_data: dict | None = None, record_id: str | None = None) -> AttendanceLog:
        
        if self.is_duplicate(db, device.id, employee_code, check_time, record_id):
            self.logger.warning(f"Duplicate attendance log for device {device.id}, employee {employee_code} at {check_time}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="السجل موجود بالفعل.")
        
        # Find employee by code and branch
        employee = db.query(Employee).filter(
            Employee.employee_code == employee_code,
            Employee.branch_id == device.branch_id,
            Employee.is_active == True
        ).first()
        
        log = AttendanceLog(
            employee_id=employee.id if employee else None,
            branch_id=device.branch_id,
            device_id=device.id,
            employee_code=employee_code,
            check_time=check_time,
            attendance_type=attendance_type,
            verify_type=verify_type,
            raw_data=raw_data,
            record_id=record_id
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        # Update device's last_sync
        device.last_sync = datetime.utcnow()
        db.commit()
        
        if not employee:
            self.logger.warning(f"Employee with code {employee_code} not found in branch {device.branch_id}")
        
        return log

    def get_stats(self, db: Session):
        today = datetime.utcnow().date()
        yesterday = today - __import__('datetime').timedelta(days=1)
        twenty_four_hours_ago = datetime.utcnow() - __import__('datetime').timedelta(hours=24)
        
        total_devices = db.query(func.count(Device.id)).scalar()
        online_devices = db.query(func.count(Device.id)).filter(Device.last_seen >= twenty_four_hours_ago).scalar()
        offline_devices = total_devices - online_devices
        logs_today = db.query(func.count(AttendanceLog.id)).filter(func.date(AttendanceLog.check_time) == today).scalar()
        
        last_log = db.query(AttendanceLog).order_by(AttendanceLog.created_at.desc()).first()
        last_device = last_log.device if last_log else None
        
        inactive_devices = db.query(Device).filter(
            (Device.last_seen < twenty_four_hours_ago) | (Device.last_seen == None)
        ).all()
        
        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "logs_today": logs_today,
            "last_log_time": last_log.created_at if last_log else None,
            "last_device_name": last_device.device_name if last_device else None,
            "inactive_devices_count": len(inactive_devices),
            "inactive_devices": inactive_devices
        }
