from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging
import asyncio

from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.models.device import Device
from app.services.device_service import DeviceService
from app.core.websocket_manager import manager

logger = logging.getLogger(__name__)

class AttendanceLogService:
    def __init__(self):
        self.device_service = DeviceService()

    def list(self, db: Session, branch_id: int | None = None, device_id: int | None = None, start_date: datetime | None = None, end_date: datetime | None = None, employee_code: str | None = None, attendance_type: str | None = None, verify_type: str | None = None) -> list:
        from app.schemas.attendance_log import AttendanceLogResponse
        
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
        
        logs = query.order_by(AttendanceLog.check_time.desc()).all()
        
        # Map to response with employee and device names
        response_logs = []
        for log in logs:
            log_dict = AttendanceLogResponse.model_validate(log).model_dump()
            # Add employee name
            if log.employee:
                log_dict["employee_name"] = f"{log.employee.first_name} {log.employee.last_name}"
            else:
                log_dict["employee_name"] = f"Unknown ({log.employee_code})"
            # Add device name
            log_dict["device_name"] = log.device.device_name
            # Translate attendance type and verify type to Arabic
            type_map = {
                "check_in": "حضور",
                "check_out": "انصراف",
                "break_in": "بداية استراحة",
                "break_out": "نهاية استراحة",
                "ot_in": "بداية وقت إضافي",
                "ot_out": "نهاية وقت إضافي"
            }
            log_dict["attendance_type"] = type_map.get(log_dict["attendance_type"], log_dict["attendance_type"] or "حضور")
            verify_map = {
                "password": "كلمة مرور",
                "fingerprint": "بصمة",
                "card": "بطاقة",
                "face": "وجه"
            }
            log_dict["verify_type"] = verify_map.get(log_dict["verify_type"], log_dict["verify_type"] or "بصمة")
            
            response_logs.append(AttendanceLogResponse(**log_dict))
        return response_logs

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
        
        logger.info(f"[AttendanceLogService] Creating log: device_id={device.id}, employee_code='{employee_code}', check_time={check_time}")
        
        if self.is_duplicate(db, device.id, employee_code, check_time, record_id):
            logger.warning(f"[AttendanceLogService] Duplicate attendance log for device {device.id}, employee {employee_code} at {check_time}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="السجل موجود بالفعل.")
        
        # Find employee by code and branch
        employee = db.query(Employee).filter(
            Employee.employee_code == employee_code,
            Employee.branch_id == device.branch_id,
            Employee.is_active == True
        ).first()
        
        if employee:
            logger.info(f"[AttendanceLogService] Found matching employee: id={employee.id}, name={employee.first_name} {employee.last_name}")
        else:
            logger.warning(f"[AttendanceLogService] No active employee found with code '{employee_code}' in branch_id={device.branch_id}")
        
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
        logger.info(f"[AttendanceLogService] Successfully created attendance log: id={log.id}")
        
        # Update device's last_sync using DeviceService
        self.device_service.update_last_sync(db, device.id)
        
        # Broadcast new log via WebSocket with all required details
        try:
            employee_name = f"{employee.first_name} {employee.last_name}" if employee else f"Unknown ({employee_code})"
            # Map attendance type to friendly text (Arabic)
            type_map = {
                "check_in": "حضور",
                "check_out": "انصراف",
                "break_in": "بداية استراحة",
                "break_out": "نهاية استراحة",
                "ot_in": "بداية وقت إضافي",
                "ot_out": "نهاية وقت إضافي"
            }
            attendance_type_text = type_map.get(log.attendance_type, log.attendance_type or "حضور")
            # Map verify type to friendly text (Arabic)
            verify_map = {
                "password": "كلمة مرور",
                "fingerprint": "بصمة",
                "card": "بطاقة",
                "face": "وجه"
            }
            verify_type_text = verify_map.get(log.verify_type, log.verify_type or "بصمة")
            message = {
                "type": "attendance_log",
                "data": {
                    "id": log.id,
                    "employee_code": employee_code,
                    "employee_name": employee_name,
                    "device_name": device.device_name,
                    "check_time": log.check_time.isoformat(),
                    "attendance_type": attendance_type_text,
                    "verify_type": verify_type_text,
                    "source": log.source
                }
            }
            # Broadcast the message via asyncio
            import asyncio
            from app.core.websocket_manager import manager
            asyncio.create_task(manager.broadcast(message))
        except Exception as e:
            logger.error(f"[AttendanceLogService] Error broadcasting log: {e}")
        
        return log

    def get_stats(self, db: Session):
        # First update all device statuses
        self.device_service.update_all_device_statuses(db)
        
        today = datetime.utcnow().date()
        twenty_four_hours_ago = datetime.utcnow() - __import__('datetime').timedelta(hours=24)
        
        total_devices = db.query(func.count(Device.id)).scalar()
        online_devices = db.query(func.count(Device.id)).filter(Device.status == "Online").scalar()
        offline_devices = total_devices - online_devices
        logs_today = db.query(func.count(AttendanceLog.id)).filter(func.date(AttendanceLog.check_time) == today).scalar()
        
        last_log = db.query(AttendanceLog).order_by(AttendanceLog.created_at.desc()).first()
        last_device = last_log.device if last_log else None
        
        inactive_devices = db.query(Device).filter(Device.status == "Offline").all()
        
        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "logs_today": logs_today,
            "last_log_time": last_log.created_at if last_log else None,
            "last_device_name": last_device.device_name if last_log else None,
            "inactive_devices_count": len(inactive_devices),
            "inactive_devices": inactive_devices
        }