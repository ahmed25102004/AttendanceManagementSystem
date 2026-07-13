from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.core.dependencies import get_admin_user, get_db
from app.models.attendance_log import AttendanceLog
from app.models.device import Device
from app.models.branch import Branch

router = APIRouter(dependencies=[Depends(get_admin_user)])


@router.get("/stats")
def get_monitoring_stats(db: Session = Depends(get_db)):
    today = date.today()
    twenty_four_hours_ago = datetime.utcnow() - __import__("datetime").timedelta(hours=24)
    
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.last_seen >= twenty_four_hours_ago).count()
    offline_devices = total_devices - online_devices
    
    logs_today = db.query(AttendanceLog).filter(
        __import__("sqlalchemy").func.date(AttendanceLog.check_time) == today
    ).count()
    
    last_log = db.query(AttendanceLog).order_by(AttendanceLog.created_at.desc()).first()
    last_device_name = None
    last_log_time = None
    if last_log:
        last_log_time = last_log.created_at
        device = db.query(Device).filter(Device.id == last_log.device_id).first()
        if device:
            last_device_name = device.device_name
    
    inactive_devices = db.query(Device).filter(
        (Device.last_seen < twenty_four_hours_ago) | (Device.last_seen == None)
    ).all()
    inactive_devices_list = []
    for d in inactive_devices:
        branch = db.query(Branch).filter(Branch.id == d.branch_id).first()
        inactive_devices_list.append({
            "id": d.id,
            "device_name": d.device_name,
            "branch_name": branch.name if branch else None,
            "last_seen": d.last_seen,
        })
    
    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "logs_today": logs_today,
        "last_device_name": last_device_name,
        "last_log_time": last_log_time,
        "inactive_devices": inactive_devices_list,
    }
