from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_shift_schedule import EmployeeShiftSchedule
from app.schemas.report import ReportRow


class ReceptionService:
    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    SHIFT_TYPE_LABELS = {
        "morning": "شيفت صباحي",
        "evening": "شيفت مسائي",
        "half": "نصف شيفت",
        "full": "شيفت كامل",
        "صباحي": "شيفت صباحي",
        "مسائي": "شيفت مسائي",
        "نصف": "نصف شيفت",
        "كامل": "شيفت كامل",
    }

    STATUS_LABELS = {
        "present": "present",
        "present_on_rest_day": "present_on_rest_day",
        "weekly_rest": "weekly_rest",
        "absent": "absent",
    }

    def is_reception_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "reception_department")
        
    def is_leather_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "leather_department")

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

    def _shift_label(self, shift_type: str | None, shift_name: str | None) -> str | None:
        if shift_name:
            return shift_name
        if not shift_type:
            return None
        return self.SHIFT_TYPE_LABELS.get(shift_type.strip().lower(), shift_type)

    def _resolve_shift_info(self, employee: Employee, target_date: date) -> dict | None:
        day_name = self._day_name(target_date)
        schedule: EmployeeShiftSchedule | None = next(
            (
                item
                for item in employee.shift_schedules
                if item.day_of_week and item.day_of_week.strip().lower() == day_name
            ),
            None,
        )

        shift = None
        shift_type = None
        if schedule:
            shift = schedule.shift or employee.shift
            shift_type = schedule.shift_type
        elif employee.shift:
            shift = employee.shift

        if not shift:
            return None

        return {
            "id": shift.id,
            "name": shift.name,
            "shift_type": shift_type,
            "label": self._shift_label(shift_type, shift.name),
            "start_time": shift.start_time,
            "end_time": shift.end_time,
            "grace_period_minutes": shift.grace_period_minutes,
        }

    def _late_minutes(self, shift_info: dict | None, check_in_time: datetime | None, is_rest_day: bool) -> int:
        if not shift_info or not check_in_time or is_rest_day:
            return 0

        shift_start = datetime.combine(check_in_time.date(), shift_info["start_time"])
        grace_period = shift_info.get("grace_period_minutes") or 0
        late_threshold = shift_start + timedelta(minutes=grace_period)
        if check_in_time > late_threshold:
            return int((check_in_time - shift_start).total_seconds() // 60)
        return 0

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
            .options(
                joinedload(Employee.department),
                joinedload(Employee.shift),
                joinedload(Employee.shift_schedules).joinedload(EmployeeShiftSchedule.shift),
            )
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
        department = db.query(Department).filter(Department.id == department_id).first()
        is_leather = self.is_leather_department(department)
        
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
                shift_info = self._resolve_shift_info(employee, current_date) if not is_leather else None
                is_rest_day = self._is_rest_day(employee, current_date) if not is_leather else False
                record = record_map.get((employee.id, current_date))
                day_logs = log_map.get((employee.id, current_date))
                if record:
                    first_log = record.check_in_time
                    last_log = record.check_out_time
                    worked_on_rest_day = record.worked_on_rest_day if not is_leather else False
                    late_minutes = record.late_minutes if not is_leather else 0
                    working_hours = round(record.working_hours, 2)
                    status = record.status
                else:
                    first_log = day_logs["first"] if day_logs else None
                    last_log = day_logs["last"] if day_logs else None
                    if first_log and last_log and last_log <= first_log:
                        last_log = None

                    worked_on_rest_day = bool(first_log and is_rest_day) if not is_leather else False
                    late_minutes = self._late_minutes(shift_info, first_log, is_rest_day) if not is_leather else 0
                    working_hours = self._working_hours(first_log, last_log)

                    if first_log:
                        status = "present_on_rest_day" if worked_on_rest_day else "present"
                    elif is_rest_day:
                        status = "weekly_rest" if not is_leather else "absent"
                    else:
                        status = "absent"

                if status == "present_on_rest_day":
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
                        shift_name=shift_info["label"] if shift_info and not is_leather else None,
                        shift_type=shift_info["shift_type"] if shift_info and not is_leather else None,
                        shift_start_time=self._format_time(shift_info["start_time"]) if shift_info and not is_leather else None,
                        shift_end_time=self._format_time(shift_info["end_time"]) if shift_info and not is_leather else None,
                        check_in_time=self._format_datetime(raw_row["first_log"]),
                        check_out_time=self._format_datetime(raw_row["last_log"]),
                        working_hours=raw_row["working_hours"],
                        status=raw_row["status"],
                        is_late=raw_row["late_minutes"] > 0 if not is_leather else False,
                        late_minutes=raw_row["late_minutes"] if not is_leather else 0,
                        worked_on_rest_day=raw_row["worked_on_rest_day"],
                        absent_days_count=absent_days_count if not is_leather else 0,
                        weekly_rest_days_count=weekly_rest_days_count if not is_leather else 0,
                        worked_on_rest_days_count=worked_on_rest_days_count if not is_leather else 0,
                    )
                )

        rows.sort(key=lambda row: (row.attendance_date, row.employee_name))
        return rows

    def get_department_today_stats(
        self,
        db: Session,
        department_id: int,
        branch_id: int | None = None,
    ) -> dict:
        department = db.query(Department).filter(Department.id == department_id).first()
        is_leather = self.is_leather_department(department)
        
        today = date.today()
        employees = self._query_department_employees(db, department_id, branch_id)
        employee_ids = [employee.id for employee in employees]
        log_map = self._build_log_map(db, employee_ids, today, today)
        record_map = self._build_record_map(db, employee_ids, today, today)

        employees_summary = []
        attendance_today = 0
        for employee in employees:
            shift_info = self._resolve_shift_info(employee, today) if not is_leather else None
            is_rest_day = self._is_rest_day(employee, today) if not is_leather else False
            record = record_map.get((employee.id, today))
            day_logs = log_map.get((employee.id, today))
            if record:
                first_log = record.check_in_time
                last_log = record.check_out_time
                late_minutes = record.late_minutes if not is_leather else 0
                worked_on_rest_day = record.worked_on_rest_day if not is_leather else False
                status = record.status
            else:
                first_log = day_logs["first"] if day_logs else None
                last_log = day_logs["last"] if day_logs else None
                if first_log and last_log and last_log <= first_log:
                    last_log = None

                late_minutes = self._late_minutes(shift_info, first_log, is_rest_day) if not is_leather else 0
                worked_on_rest_day = bool(first_log and is_rest_day) if not is_leather else False
                status = "present" if first_log and not worked_on_rest_day else "present_on_rest_day" if worked_on_rest_day else "weekly_rest" if is_rest_day else "absent"
            if first_log:
                attendance_today += 1

            employees_summary.append(
                {
                    "id": employee.id,
                    "full_name": self._employee_full_name(employee),
                    "employee_code": employee.employee_code,
                    "attendance_today": bool(first_log),
                    "status": status,
                    "weekly_rest_day": employee.weekly_rest_day if not is_leather else None,
                    "shift_name": shift_info["label"] if shift_info and not is_leather else None,
                    "shift_type": shift_info["shift_type"] if shift_info and not is_leather else None,
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
