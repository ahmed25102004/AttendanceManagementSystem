from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
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
