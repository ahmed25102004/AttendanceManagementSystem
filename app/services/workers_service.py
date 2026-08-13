from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.report import ReportRow


class WorkersService:
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def _format_time(self, value: time | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%H:%M")

    def _format_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    def _employee_full_name(self, employee: Employee) -> str:
        return " ".join(part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip())

    def _day_name(self, target_date: date) -> str:
        return self.DAY_NAMES[target_date.weekday()]

    def _is_rest_day(self, employee: Employee, target_date: date) -> bool:
        if not employee.weekly_rest_day:
            return False
        return employee.weekly_rest_day.strip().lower() == self._day_name(target_date)

    def _resolve_shift_info(self, employee: Employee, first_log: datetime | None = None) -> dict | None:
        """
        تحديد الشيفت تلقائيًا بناءً على أول بصمة.
        إذا لم يكن هناك بصمة، يتم إرجاع الشيفت الأول كافتراضي.
        """
        dept = employee.department
        if not dept:
            return None

        shift1_start = dept.shift_start_time
        shift1_late = dept.late_start_time
        shift1_end = dept.shift_end_time

        shift2_start = dept.evening_shift_start_time
        shift2_late = dept.evening_shift_late_start_time
        shift2_end = dept.evening_shift_end_time

        # Default to shift 1 if no logs
        if not first_log or not shift2_start:
            return {
                "label": "الشيفت الأول",
                "shift_type": "morning",
                "start_time": shift1_start,
                "late_time": shift1_late,
                "end_time": shift1_end,
            }

        first_log_time = first_log.time()
        
        if first_log_time >= shift2_start:
            return {
                "label": "الشيفت الثاني",
                "shift_type": "evening",
                "start_time": shift2_start,
                "late_time": shift2_late,
                "end_time": shift2_end,
            }
        else:
            return {
                "label": "الشيفت الأول",
                "shift_type": "morning",
                "start_time": shift1_start,
                "late_time": shift1_late,
                "end_time": shift1_end,
            }

    def _late_minutes(self, shift_info: dict | None, check_in_time: datetime | None, is_rest_day: bool) -> int:
        # Per user spec: late/deficit/overtime are calculated NORMALLY on rest day too
        if not shift_info or not check_in_time or not shift_info.get("late_time"):
            return 0

        late_threshold_time = shift_info["late_time"]
        late_threshold = datetime.combine(check_in_time.date(), late_threshold_time)

        # Late minutes = minutes AFTER grace end (NOT from shift start)
        # Matches user spec: 8:00 start, 8:30 grace, 8:45 check-in → 15 min late
        if check_in_time > late_threshold:
            return int((check_in_time - late_threshold).total_seconds() // 60)
        return 0

    def _shift_deficit_hours(self, shift_info: dict | None, check_out_time: datetime | None, is_rest_day: bool) -> float:
        # Per user spec: deficit calculated normally on rest day too
        if not shift_info or not check_out_time or not shift_info.get("end_time"):
            return 0.0

        shift_end = datetime.combine(check_out_time.date(), shift_info["end_time"])
        if check_out_time < shift_end:
            return round((shift_end - check_out_time).total_seconds() / 3600, 2)
        return 0.0

    def _overtime_hours(self, shift_info: dict | None, check_out_time: datetime | None, is_rest_day: bool) -> float:
        # Per user spec: overtime calculated normally on rest day too
        if not shift_info or not check_out_time or not shift_info.get("end_time"):
            return 0.0

        shift_end = datetime.combine(check_out_time.date(), shift_info["end_time"])
        if check_out_time > shift_end:
            return round((check_out_time - shift_end).total_seconds() / 3600, 2)
        return 0.0

    def _working_hours(self, first_log: datetime | None, last_log: datetime | None) -> float:
        if not first_log or not last_log or last_log <= first_log:
            return 0.0
        return round((last_log - first_log).total_seconds() / 3600, 2)

    def _iter_dates(self, start_date: date, end_date: date):
        current = start_date
        while current <= end_date:
            yield current
            current += timedelta(days=1)

    def _build_log_map(
        self,
        db: Session,
        employee_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> dict[tuple[int, date], dict[str, datetime]]:
        if not employee_ids:
            return {}

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
        logs = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.employee_id.in_(employee_ids),
                AttendanceLog.check_time >= start_dt,
                AttendanceLog.check_time < end_dt,
            )
            .order_by(AttendanceLog.check_time.asc())
            .all()
        )

        grouped: dict[tuple[int, date], dict[str, datetime]] = {}
        for log in logs:
            if not log.employee_id:
                continue
            key = (log.employee_id, log.check_time.date())
            if key not in grouped:
                grouped[key] = {"first": log.check_time, "last": log.check_time}
                continue
            if log.check_time < grouped[key]["first"]:
                grouped[key]["first"] = log.check_time
            if log.check_time > grouped[key]["last"]:
                grouped[key]["last"] = log.check_time
        return grouped

    def _build_record_map(
        self,
        db: Session,
        employee_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> dict[tuple[int, date], AttendanceRecord]:
        if not employee_ids:
            return {}

        records = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id.in_(employee_ids),
                AttendanceRecord.attendance_date >= start_date,
                AttendanceRecord.attendance_date <= end_date,
            )
            .all()
        )
        return {(record.employee_id, record.attendance_date): record for record in records}

    def _query_department_employees(
        self,
        db: Session,
        department_id: int,
        branch_id: int | None = None,
    ) -> list[Employee]:
        query = (
            db.query(Employee)
            .options(joinedload(Employee.department))
            .filter(Employee.department_id == department_id, Employee.is_active.is_(True))
        )
        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)
        return query.order_by(Employee.first_name.asc(), Employee.id.asc()).all()

    def build_report_rows(
        self,
        db: Session,
        department_id: int,
        start_date: date,
        end_date: date,
        branch_id: int | None = None,
    ) -> list[ReportRow]:
        
        employees = self._query_department_employees(db, department_id, branch_id)
        employee_ids = [employee.id for employee in employees]
        log_map = self._build_log_map(db, employee_ids, start_date, end_date)
        record_map = self._build_record_map(db, employee_ids, start_date, end_date)

        rows: list[ReportRow] = []
        for employee in employees:
            raw_rows: list[dict] = []
            absent_days_count = 0
            weekly_rest_days_count = 0
            worked_on_rest_days_count = 0

            for current_date in self._iter_dates(start_date, end_date):
                is_rest_day = self._is_rest_day(employee, current_date)
                record = record_map.get((employee.id, current_date))
                day_logs = log_map.get((employee.id, current_date))
                
                if record:
                    first_log = record.check_in_time
                    last_log = record.check_out_time
                else:
                    first_log = day_logs["first"] if day_logs else None
                    last_log = day_logs["last"] if day_logs else None
                    if first_log and last_log and last_log <= first_log:
                        last_log = None

                shift_info = self._resolve_shift_info(employee, first_log)

                worked_on_rest_day = bool(first_log and is_rest_day)

                if record and record.is_manual_attendance and record.working_hours is not None:
                    working_hours = round(record.working_hours, 2)
                    late_minutes = record.late_minutes or 0
                    shift_deficit_hours = 0.0
                    overtime_hours = 0.0
                    status = record.status
                else:
                    late_minutes = self._late_minutes(shift_info, first_log, is_rest_day)
                    working_hours = self._working_hours(first_log, last_log)
                    shift_deficit_hours = self._shift_deficit_hours(shift_info, last_log, is_rest_day)
                    overtime_hours = self._overtime_hours(shift_info, last_log, is_rest_day)

                    if first_log:
                        # Required: "إذا حضر الموظف في يوم الإجازة الأسبوعية: يتم تسجيله كـ "حاضر"."
                        status = "present"
                    elif is_rest_day:
                        status = "weekly_rest"
                    else:
                        status = "absent"

                if worked_on_rest_day:
                    worked_on_rest_days_count += 1
                elif status == "weekly_rest":
                    weekly_rest_days_count += 1
                elif status == "absent":
                    absent_days_count += 1

                raw_rows.append(
                    {
                        "current_date": current_date,
                        "shift_info": shift_info,
                        "first_log": first_log,
                        "last_log": last_log,
                        "working_hours": working_hours,
                        "late_minutes": late_minutes,
                        "shift_deficit_hours": shift_deficit_hours,
                        "overtime_hours": overtime_hours,
                        "status": status,
                        "worked_on_rest_day": worked_on_rest_day,
                    }
                )

            for raw_row in raw_rows:
                shift_info = raw_row["shift_info"]
                rows.append(
                    ReportRow(
                        employee_code=employee.employee_code,
                        employee_name=self._employee_full_name(employee),
                        department=employee.department.name if employee.department else None,
                        job_title=employee.job_title,
                        attendance_date=raw_row["current_date"].isoformat(),
                        shift_name=shift_info["label"] if shift_info else None,
                        shift_type=shift_info["shift_type"] if shift_info else None,
                        shift_start_time=self._format_time(shift_info["start_time"]) if shift_info else None,
                        shift_end_time=self._format_time(shift_info["end_time"]) if shift_info else None,
                        check_in_time=self._format_datetime(raw_row["first_log"]),
                        check_out_time=self._format_datetime(raw_row["last_log"]),
                        working_hours=raw_row["working_hours"],
                        status=raw_row["status"],
                        is_late=raw_row["late_minutes"] > 0,
                        late_minutes=raw_row["late_minutes"],
                        shift_deficit_hours=raw_row["shift_deficit_hours"],
                        overtime_hours=raw_row["overtime_hours"],
                        worked_on_rest_day=raw_row["worked_on_rest_day"],
                        absent_days_count=absent_days_count,
                        weekly_rest_days_count=weekly_rest_days_count,
                        worked_on_rest_days_count=worked_on_rest_days_count,
                    )
                )

        # Sort by employee name, then code, then date
        rows.sort(key=lambda r: (r.employee_name or "", r.employee_code or "", r.attendance_date))
        return rows

    def get_department_today_stats(
        self,
        db: Session,
        department_id: int,
        branch_id: int | None = None,
    ) -> dict:
        """Get today's stats for workers department with auto-shift detection."""
        today = date.today()
        employees = self._query_department_employees(db, department_id, branch_id)
        employee_ids = [employee.id for employee in employees]
        log_map = self._build_log_map(db, employee_ids, today, today)
        record_map = self._build_record_map(db, employee_ids, today, today)

        employees_summary = []
        attendance_today = 0
        for employee in employees:
            is_rest_day = self._is_rest_day(employee, today)
            record = record_map.get((employee.id, today))
            day_logs = log_map.get((employee.id, today))

            if record:
                first_log = record.check_in_time
                last_log = record.check_out_time
                late_minutes = record.late_minutes or 0
                worked_on_rest_day = record.worked_on_rest_day or False
                status = record.status
            else:
                first_log = day_logs["first"] if day_logs else None
                last_log = day_logs["last"] if day_logs else None
                if first_log and last_log and last_log <= first_log:
                    last_log = None

                shift_info = self._resolve_shift_info(employee, first_log)
                late_minutes = self._late_minutes(shift_info, first_log, is_rest_day)
                worked_on_rest_day = bool(first_log and is_rest_day)

                if first_log:
                    status = "present"
                elif is_rest_day:
                    status = "weekly_rest"
                else:
                    status = "absent"

            shift_info = self._resolve_shift_info(employee, first_log)
            if first_log:
                attendance_today += 1

            employees_summary.append(
                {
                    "id": employee.id,
                    "full_name": self._employee_full_name(employee),
                    "employee_code": employee.employee_code,
                    "attendance_today": bool(first_log),
                    "status": status,
                    "weekly_rest_day": employee.weekly_rest_day,
                    "shift_name": shift_info["label"] if shift_info else None,
                    "shift_type": shift_info["shift_type"] if shift_info else None,
                    "check_in_time": first_log,
                    "check_out_time": last_log,
                    "late_minutes": late_minutes,
                    "worked_on_rest_day": worked_on_rest_day,
                }
            )

        latest_logs = []
        if employee_ids:
            records = (
                db.query(AttendanceLog)
                .options(joinedload(AttendanceLog.employee))
                .filter(AttendanceLog.employee_id.in_(employee_ids))
                .order_by(AttendanceLog.check_time.desc())
                .limit(10)
                .all()
            )
            for log in records:
                latest_logs.append(
                    {
                        "id": log.id,
                        "employee_id": log.employee_id,
                        "employee_name": self._employee_full_name(log.employee) if log.employee else None,
                        "attendance_date": log.check_time.date(),
                        "check_in_time": log.check_time,
                        "check_out_time": None,
                        "is_late": False,
                        "working_hours": 0.0,
                    }
                )

        return {
            "attendance_today": attendance_today,
            "employees": employees_summary,
            "latest_attendance": latest_logs,
        }
