from datetime import date, datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.branch import Branch
from app.models.employee import Employee
from app.models.device import Device
from app.models.attendance_log import AttendanceLog
from app.schemas.branch import BranchCreate, BranchUpdate


class BranchService:
    def list(self, db: Session) -> list[Branch]:
        return db.query(Branch).order_by(Branch.id.desc()).all()

    def get(self, db: Session, branch_id: int) -> Branch:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفرع غير موجود.")
        return branch

    def create(self, db: Session, payload: BranchCreate) -> Branch:
        if db.query(Branch).filter(Branch.name == payload.name).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الفرع موجود بالفعل.")
        branch = Branch(**payload.model_dump())
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return branch

    def update(self, db: Session, branch_id: int, payload: BranchUpdate) -> Branch:
        branch = self.get(db, branch_id)
        if payload.name:
            existing = db.query(Branch).filter(Branch.name == payload.name, Branch.id != branch_id).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم الفرع مستخدم بالفعل.")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(branch, key, value)
        db.commit()
        db.refresh(branch)
        return branch

    def delete(self, db: Session, branch_id: int) -> None:
        branch = self.get(db, branch_id)
        db.delete(branch)
        db.commit()

    def get_stats(self, db: Session, branch_id: int) -> dict:
        # Check branch exists
        self.get(db, branch_id)
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

        total_employees = db.query(func.count(Employee.id)).filter(Employee.branch_id == branch_id, Employee.is_active.is_(True)).scalar()
        total_devices = db.query(func.count(Device.id)).filter(Device.branch_id == branch_id, Device.is_active.is_(True)).scalar()
        online_devices = db.query(func.count(Device.id)).filter(
            Device.branch_id == branch_id,
            Device.is_active.is_(True),
            Device.last_seen >= twenty_four_hours_ago
        ).scalar()
        logs_today = db.query(func.count(AttendanceLog.id)).filter(
            AttendanceLog.branch_id == branch_id,
            func.date(AttendanceLog.check_time) == today
        ).scalar()

        # Get today's attendance (unique employees who checked in)
        today_attendance_employees = db.query(
            func.count(func.distinct(AttendanceLog.employee_code))
        ).filter(
            AttendanceLog.branch_id == branch_id,
            func.date(AttendanceLog.check_time) == today
        ).scalar()

        # Get inactive devices
        inactive_devices = db.query(Device).filter(
            Device.branch_id == branch_id,
            (Device.last_seen < twenty_four_hours_ago) | (Device.last_seen == None)
        ).all()

        # Get latest logs
        latest_logs = db.query(AttendanceLog).options(
            joinedload(AttendanceLog.employee),
            joinedload(AttendanceLog.device)
        ).filter(
            AttendanceLog.branch_id == branch_id
        ).order_by(AttendanceLog.check_time.desc()).limit(10).all()

        return {
            "id": branch_id,
            "name": self.get(db, branch_id).name,
            "total_employees": total_employees,
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "logs_today": logs_today,
            "attendance_today": today_attendance_employees,
            "inactive_devices": [
                {
                    "id": d.id,
                    "device_name": d.device_name,
                    "last_seen": d.last_seen
                }
                for d in inactive_devices
            ],
            "latest_logs": [
                {
                    "id": l.id,
                    "employee_code": l.employee_code,
                    "employee_name": l.employee.full_name if l.employee else None,
                    "device_name": l.device.device_name if l.device else None,
                    "check_time": l.check_time,
                    "attendance_type": l.attendance_type,
                    "verify_type": l.verify_type
                }
                for l in latest_logs
            ]
        }
    
    def get_all_stats(self, db: Session) -> list[dict]:
        branches = self.list(db)
        all_stats = []
        for branch in branches:
            if branch.is_active:
                try:
                    stats = self.get_stats(db, branch.id)
                    all_stats.append(stats)
                except Exception as e:
                    # Skip branches with errors
                    continue
        return all_stats
