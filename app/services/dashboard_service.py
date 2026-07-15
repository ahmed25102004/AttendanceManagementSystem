from datetime import date, timedelta, datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.device import Device
from app.models.branch import Branch
from app.models.attendance_log import AttendanceLog
from app.schemas.report import DashboardSummary, WeeklyAttendanceData


class DashboardService:
    def get_summary(self, db: Session) -> DashboardSummary:
        today = date.today()
        total_employees = db.query(Employee).filter(Employee.is_active.is_(True)).count()
        present_today = db.query(AttendanceRecord).filter(AttendanceRecord.attendance_date == today).count()
        late_employees = db.query(AttendanceRecord).filter(
            AttendanceRecord.attendance_date == today, AttendanceRecord.is_late.is_(True)
        ).count()
        absent_today = max(total_employees - present_today, 0)
        attendance_rate = round((present_today / total_employees) * 100, 2) if total_employees else 0.0

        # Get weekly data for last 7 days
        labels = []
        present = []
        late = []
        day_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

        for i in range(6, -1, -1):  # last 7 days, from 6 days ago to today
            current_date = today - timedelta(days=i)
            # Use Arabic day name
            day_name = day_names[current_date.weekday()]
            labels.append(f"{day_name} ({current_date.day}/{current_date.month})")

            # Count present and late
            day_present = db.query(AttendanceRecord).filter(AttendanceRecord.attendance_date == current_date).count()
            day_late = db.query(AttendanceRecord).filter(
                AttendanceRecord.attendance_date == current_date,
                AttendanceRecord.is_late.is_(True)
            ).count()

            present.append(day_present)
            late.append(day_late)

        weekly_data = WeeklyAttendanceData(
            labels=labels,
            present=present,
            late=late
        )

        return DashboardSummary(
            total_employees=total_employees,
            present_today=present_today,
            absent_today=absent_today,
            late_employees=late_employees,
            attendance_rate=attendance_rate,
            weekly_data=weekly_data
        )
        
    def get_overall_kpis(self, db: Session) -> dict:
        today = date.today()
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        total_employees = db.query(Employee).filter(Employee.is_active.is_(True)).count()
        total_branches = db.query(Branch).filter(Branch.is_active.is_(True)).count()
        total_devices = db.query(Device).filter(Device.is_active.is_(True)).count()
        online_devices = db.query(Device).filter(
            Device.is_active.is_(True),
            Device.last_seen >= twenty_four_hours_ago
        ).count()
        
        # Get today's unique check-ins
        unique_today_checkins = db.query(func.count(func.distinct(AttendanceLog.employee_id))).filter(
            func.date(AttendanceLog.check_time) == today,
            AttendanceLog.attendance_type.in_(["check_in", "0"])
        ).scalar() or 0
        
        # Get employees currently working (last log is check_in)
        subquery = db.query(
            AttendanceLog.employee_id,
            func.max(AttendanceLog.check_time).label('last_check')
        ).filter(
            func.date(AttendanceLog.check_time) == today
        ).group_by(AttendanceLog.employee_id).subquery()
        
        currently_working = db.query(func.count(AttendanceLog.id)).join(
            subquery, 
            and_(AttendanceLog.employee_id == subquery.c.employee_id, 
                 AttendanceLog.check_time == subquery.c.last_check)
        ).filter(
            AttendanceLog.attendance_type.in_(["check_in", "0", "3", "4"])
        ).scalar() or 0
        
        # Get late check-ins today
        late_checkins = 0
        
        return {
            "total_employees": total_employees,
            "total_branches": total_branches,
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "present_today": unique_today_checkins,
            "absent_today": total_employees - unique_today_checkins,
            "currently_working": currently_working,
            "late_checkins": late_checkins
        }
        
    def get_branches_stats(self, db: Session) -> list[dict]:
        branches = db.query(Branch).filter(Branch.is_active.is_(True)).all()
        today = date.today()
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        result = []
        for branch in branches:
            branch_employees = db.query(Employee).filter(
                Employee.branch_id == branch.id, 
                Employee.is_active.is_(True)
            ).count()
            
            branch_checkins = db.query(func.count(func.distinct(AttendanceLog.employee_id))).filter(
                func.date(AttendanceLog.check_time) == today,
                AttendanceLog.branch_id == branch.id,
                AttendanceLog.attendance_type.in_(["check_in", "0"])
            ).scalar() or 0
            
            branch_devices = db.query(Device).filter(
                Device.branch_id == branch.id, 
                Device.is_active.is_(True)
            ).count()
            
            branch_online_devices = db.query(Device).filter(
                Device.branch_id == branch.id, 
                Device.is_active.is_(True),
                Device.last_seen >= twenty_four_hours_ago
            ).count()
            
            attendance_rate = round((branch_checkins / branch_employees) * 100, 1) if branch_employees else 0
            
            result.append({
                "id": branch.id,
                "name": branch.name,
                "total_employees": branch_employees,
                "present_today": branch_checkins,
                "attendance_rate": attendance_rate,
                "total_devices": branch_devices,
                "online_devices": branch_online_devices
            })
            
        return result
    
    def get_alerts(self, db: Session) -> list[dict]:
        today = date.today()
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        alerts = []
        
        # Offline devices
        offline_devices = db.query(Device).options(joinedload(Device.branch)).filter(
            Device.is_active.is_(True),
            or_(
                Device.last_seen < twenty_four_hours_ago,
                Device.last_seen == None
            )
        ).all()
        
        for dev in offline_devices:
            alerts.append({
                "type": "device_offline",
                "title": "جهاز مفصل",
                "message": f"{dev.device_name} - {dev.branch.name if dev.branch else ''}",
                "time": dev.last_seen
            })
            
        # Employees without check-out
        # First get employees who checked in but not out yet
        subquery_checkins = db.query(
            AttendanceLog.employee_id,
            func.max(AttendanceLog.check_time).label('last_check_in_time')
        ).filter(
            func.date(AttendanceLog.check_time) == today,
            AttendanceLog.attendance_type.in_(["check_in", "0", "3", "4"])
        ).group_by(AttendanceLog.employee_id).subquery()
        
        subquery_checkouts = db.query(
            AttendanceLog.employee_id,
            func.max(AttendanceLog.check_time).label('last_check_out_time')
        ).filter(
            func.date(AttendanceLog.check_time) == today,
            AttendanceLog.attendance_type.in_(["check_out", "1", "2", "5"])
        ).group_by(AttendanceLog.employee_id).subquery()
        
        employees_no_checkout = db.query(Employee).options(
            joinedload(Employee.branch)
        ).join(
            subquery_checkins,
            Employee.id == subquery_checkins.c.employee_id
        ).outerjoin(
            subquery_checkouts,
            and_(
                Employee.id == subquery_checkouts.c.employee_id,
                subquery_checkouts.c.last_check_out_time > subquery_checkins.c.last_check_in_time
            )
        ).filter(
            Employee.is_active.is_(True),
            subquery_checkouts.c.last_check_out_time == None
        ).all()
        
        for emp in employees_no_checkout:
            alerts.append({
                "type": "no_checkout",
                "title": "موظف بدون انصراف",
                "message": f"{emp.full_name} - {emp.branch.name if emp.branch else ''}",
                "time": None
            })
            
        return alerts
    
    def get_recent_logs(self, db: Session, limit: int = 15) -> list[dict]:
        logs = db.query(AttendanceLog).options(
            joinedload(AttendanceLog.employee),
            joinedload(AttendanceLog.device),
            joinedload(AttendanceLog.branch)
        ).order_by(AttendanceLog.check_time.desc()).limit(limit).all()
        
        return [{
            "id": log.id,
            "employee_id": log.employee_id,
            "employee_code": log.employee_code,
            "employee_name": log.employee.full_name if log.employee else None,
            "branch_name": log.branch.name if log.branch else None,
            "device_name": log.device.device_name if log.device else None,
            "check_time": log.check_time.isoformat(),
            "attendance_type": log.attendance_type,
            "verify_type": log.verify_type
        } for log in logs]
