from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.department import Department
from app.models.employee import Employee
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

    def is_doctors_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "doctors_department")

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


    def _late_minutes(self, shift_info: dict | None, check_in_time: datetime | None, is_rest_day: bool) -> int:
        if not shift_info or not check_in_time or is_rest_day:
            return 0

        shift_start = datetime.combine(check_in_time.date(), shift_info["start_time"])
        grace_period = shift_info.get("grace_period_minutes") or 0
        late_threshold = shift_start + timedelta(minutes=grace_period)
        if check_in_time > late_threshold:
            return int((check_in_time - shift_start).total_seconds() // 60)
        return 0

    def _effective_check_in_and_late(
        self,
        first_log: datetime | None,
        emp_dept: Department | None,
        shift_info: dict | None = None,
        is_doctors: bool = False,
    ) -> tuple[datetime | None, int]:
        """
        Calculates effective check-in time and late minutes based on department grace period.
        If employee arrives within the allowed grace period:
        - late_minutes = 0
        - effective_check_in = scheduled shift start time (so grace minutes are NOT deducted from work hours)
        If employee arrives after grace period:
        - late_minutes = calculated late minutes
        - effective_check_in = first_log (late time is not counted in work hours)
        """
        if not first_log or not emp_dept:
            return first_log, 0

        target_date = first_log.date()

        if is_doctors:
            m_start = emp_dept.shift_start_time or time(8, 0)
            if emp_dept.late_start_time:
                m_grace_dt = datetime.combine(target_date, emp_dept.late_start_time)
            elif getattr(emp_dept, "grace_period_minutes", None):
                m_grace_dt = datetime.combine(target_date, m_start) + timedelta(minutes=emp_dept.grace_period_minutes)
            else:
                m_grace_dt = datetime.combine(target_date, m_start) + timedelta(minutes=15)

            ev_start = getattr(emp_dept, "evening_shift_start_time", None)
            if ev_start:
                ev_hour = ev_start.hour
                if 0 < ev_hour < 12:
                    ev_hour += 12
                ev_start = time(ev_hour, ev_start.minute)
            else:
                ev_start = time(15, 0)

            ev_grace_time = getattr(emp_dept, "evening_shift_late_start_time", None)
            if ev_grace_time:
                ev_grace_hour = ev_grace_time.hour
                if 0 < ev_grace_hour < 12:
                    ev_grace_hour += 12
                ev_grace_dt = datetime.combine(target_date, time(ev_grace_hour, ev_grace_time.minute))
            else:
                grace_mins = getattr(emp_dept, "grace_period_minutes", None)
                if grace_mins is None and emp_dept.shift_start_time and emp_dept.late_start_time:
                    t1 = datetime.combine(target_date, emp_dept.shift_start_time)
                    t2 = datetime.combine(target_date, emp_dept.late_start_time)
                    grace_mins = max(0, int((t2 - t1).total_seconds() // 60)) or 15
                ev_grace_dt = datetime.combine(target_date, ev_start) + timedelta(minutes=(grace_mins or 15))

            # Determine whether doctor came for morning/full shift or evening shift
            if first_log.time() < time(13, 0):
                sched_dt = datetime.combine(target_date, m_start)
                grace_dt = m_grace_dt
            else:
                sched_dt = datetime.combine(target_date, ev_start)
                grace_dt = ev_grace_dt

            if first_log <= grace_dt:
                late_mins = 0
                effective_in = min(first_log, sched_dt)
            else:
                late_mins = max(0, int((first_log - grace_dt).total_seconds() // 60))
                effective_in = first_log

            return effective_in, late_mins

        else:
            # Reception, workers, or other unified shifts
            start_t = shift_info["start_time"] if shift_info and "start_time" in shift_info else emp_dept.shift_start_time
            if not start_t:
                return first_log, 0

            sched_dt = datetime.combine(target_date, start_t)
            grace_mins = (shift_info.get("grace_period_minutes") if shift_info else None) or getattr(emp_dept, "grace_period_minutes", None)
            if grace_mins is None:
                if emp_dept.late_start_time:
                    t1 = datetime.combine(target_date, start_t)
                    t2 = datetime.combine(target_date, emp_dept.late_start_time)
                    grace_mins = max(0, int((t2 - t1).total_seconds() // 60))
                else:
                    grace_mins = 15

            grace_dt = sched_dt + timedelta(minutes=grace_mins)

            if first_log <= grace_dt:
                late_mins = 0
                effective_in = min(first_log, sched_dt)
            else:
                late_mins = max(0, int((first_log - sched_dt).total_seconds() // 60))
                effective_in = first_log

            return effective_in, late_mins

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
        department_id: int | None = None,
        branch_id: int | None = None,
    ) -> list[Employee]:
        query = (
            db.query(Employee)
            .options(
                joinedload(Employee.department),
            )
            .filter(Employee.is_active.is_(True))
        )
        if department_id:
            query = query.filter(Employee.department_id == department_id)
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
        department = db.query(Department).filter(Department.id == department_id).first() if department_id else None
        employees = self._query_department_employees(db, department_id, branch_id)
        return self._build_rows_for_employees(db, employees, start_date, end_date, department)

    def _build_rows_for_employees(
        self,
        db: Session,
        employees: list[Employee],
        start_date: date,
        end_date: date,
        department: Department | None = None,
    ) -> list[ReportRow]:
        if not employees:
            return []

        employee_ids = [employee.id for employee in employees]
        log_map = self._build_log_map(db, employee_ids, start_date, end_date)
        record_map = self._build_record_map(db, employee_ids, start_date, end_date)

        rows: list[ReportRow] = []
        for employee in employees:
            emp_dept = employee.department or department
            is_leather = self.is_leather_department(emp_dept)
            is_doctors = self.is_doctors_department(emp_dept)

            raw_rows: list[dict] = []
            absent_days_count = 0
            weekly_rest_days_count = 0
            worked_on_rest_days_count = 0

            for current_date in self._iter_dates(start_date, end_date):
                shift_info = self._resolve_shift_info(employee, current_date) if not (is_leather or is_doctors) else None
                is_rest_day = self._is_rest_day(employee, current_date) if not (is_leather or is_doctors) else False
                record = record_map.get((employee.id, current_date))
                day_logs = log_map.get((employee.id, current_date))
                if record:
                    first_log = record.check_in_time
                    last_log = record.check_out_time
                    worked_on_rest_day = bool(record.worked_on_rest_day) if not (is_leather or is_doctors) else False
                    is_manual = bool(getattr(record, "is_manual_attendance", False) or getattr(record, "source_type", "") == "manual")
                    if is_manual and record.working_hours is not None:
                        working_hours = round(record.working_hours, 2)
                        late_minutes = record.late_minutes if not is_leather else 0
                    else:
                        effective_first_log, auto_late = self._effective_check_in_and_late(
                            first_log, emp_dept, shift_info=shift_info, is_doctors=is_doctors
                        )
                        working_hours = self._working_hours(effective_first_log, last_log)
                        late_minutes = auto_late if not is_leather else 0

                    overtime_hours = round(getattr(record, "overtime_hours", 0.0) or 0.0, 2)
                    shift_deficit_hours = round(getattr(record, "shift_deficit_hours", 0.0) or 0.0, 2)
                    status = record.status or ("present" if first_log else "absent")
                else:
                    first_log = day_logs["first"] if day_logs else None
                    last_log = day_logs["last"] if day_logs else None
                    if first_log and last_log and last_log <= first_log:
                        last_log = None

                    effective_first_log, auto_late = self._effective_check_in_and_late(
                        first_log, emp_dept, shift_info=shift_info, is_doctors=is_doctors
                    )
                    working_hours = self._working_hours(effective_first_log, last_log)
                    late_minutes = auto_late if not is_leather else 0
                    overtime_hours = 0.0
                    shift_deficit_hours = 0.0
                    worked_on_rest_day = False
                    status = "present" if first_log else "absent"

                if is_leather:
                    worked_on_rest_day = False
                    late_minutes = 0
                    overtime_hours = 0.0
                    shift_deficit_hours = 0.0
                    status = "present" if first_log else "absent"
                elif is_doctors:
                    worked_on_rest_day = False
                    shift_hours = emp_dept.shift_hours if (emp_dept and emp_dept.shift_hours) else 7
                    full_shift_hours = shift_hours * 2
                    overtime_hours = round(working_hours - full_shift_hours, 2) if working_hours > full_shift_hours else 0.0
                    shift_deficit_hours = round(shift_hours - working_hours, 2) if (0 < working_hours < shift_hours) else 0.0
                    status = "present" if first_log else "absent"
                else:
                    worked_on_rest_day = bool(first_log and is_rest_day)
                    if shift_info and last_log and shift_info.get("end_time"):
                        shift_end = datetime.combine(last_log.date(), shift_info["end_time"])
                        if last_log > shift_end:
                            overtime_hours = round((last_log - shift_end).total_seconds() / 3600, 2)
                        if last_log < shift_end and first_log:
                            shift_deficit_hours = round((shift_end - last_log).total_seconds() / 3600, 2)

                    if first_log:
                        status = "present_on_rest_day" if worked_on_rest_day else "present"
                    elif is_rest_day:
                        status = "weekly_rest"
                    else:
                        status = "absent"

                if status == "present_on_rest_day":
                    worked_on_rest_days_count += 1
                elif status == "weekly_rest":
                    weekly_rest_days_count += 1
                elif status == "absent":
                    absent_days_count += 1

                # Calculate shift units & labels
                if is_doctors:
                    shift_hours = emp_dept.shift_hours if (emp_dept and emp_dept.shift_hours) else 7
                    full_shift_hours = shift_hours * 2
                    is_full = working_hours >= (full_shift_hours - 0.05)
                    is_half = not is_full and (working_hours >= (shift_hours - 0.05))
                    full_shift_count = 1 if is_full else 0
                    half_shift_count = 1 if is_half else 0
                    total_shift_units = 1.0 if is_full else (0.5 if is_half else 0.0)
                    shift_name = "شفت كامل" if is_full else ("نصف شيفت" if is_half else ("نقص في الشفت" if working_hours > 0 else None))
                    shift_type = "full_shift" if is_full else ("half_shift" if is_half else ("incomplete" if working_hours > 0 else None))
                    shift_start_time = self._format_time(emp_dept.shift_start_time) if emp_dept else None
                    shift_end_time = self._format_time(emp_dept.shift_end_time) if emp_dept else None
                elif is_leather:
                    full_shift_count = 0
                    half_shift_count = 0
                    total_shift_units = 0.0
                    shift_name = None
                    shift_type = None
                    shift_start_time = None
                    shift_end_time = None
                else:
                    full_shift_count = 0
                    half_shift_count = 0
                    total_shift_units = 0.0
                    shift_name = shift_info["label"] if shift_info else None
                    shift_type = shift_info["shift_type"] if shift_info else None
                    shift_start_time = self._format_time(shift_info["start_time"]) if shift_info else None
                    shift_end_time = self._format_time(shift_info["end_time"]) if shift_info else None

                raw_rows.append(
                    {
                        "current_date": current_date,
                        "shift_name": shift_name,
                        "shift_type": shift_type,
                        "shift_start_time": shift_start_time,
                        "shift_end_time": shift_end_time,
                        "first_log": first_log,
                        "last_log": last_log,
                        "working_hours": working_hours,
                        "overtime_hours": overtime_hours,
                        "shift_deficit_hours": shift_deficit_hours,
                        "late_minutes": late_minutes,
                        "status": status,
                        "worked_on_rest_day": worked_on_rest_day,
                        "full_shift_count": full_shift_count,
                        "half_shift_count": half_shift_count,
                        "total_shift_units": total_shift_units,
                    }
                )

            dept_name = emp_dept.name if emp_dept else None
            emp_name = self._employee_full_name(employee)

            for raw_row in raw_rows:
                rows.append(
                    ReportRow(
                        row_kind="daily",
                        employee_code=employee.employee_code,
                        employee_name=emp_name,
                        department=dept_name,
                        job_title=employee.job_title,
                        attendance_date=raw_row["current_date"].isoformat(),
                        shift_name=raw_row["shift_name"],
                        shift_type=raw_row["shift_type"],
                        shift_start_time=raw_row["shift_start_time"],
                        shift_end_time=raw_row["shift_end_time"],
                        check_in_time=self._format_datetime(raw_row["first_log"]),
                        check_out_time=self._format_datetime(raw_row["last_log"]),
                        working_hours=raw_row["working_hours"],
                        overtime_hours=raw_row.get("overtime_hours", 0.0),
                        shift_deficit_hours=raw_row.get("shift_deficit_hours", 0.0),
                        status=raw_row["status"],
                        is_late=raw_row["late_minutes"] > 0 if not is_leather else False,
                        late_minutes=raw_row["late_minutes"] if not is_leather else 0,
                        worked_on_rest_day=raw_row["worked_on_rest_day"],
                        absent_days_count=absent_days_count if not is_leather else 0,
                        weekly_rest_days_count=weekly_rest_days_count if not (is_leather or is_doctors) else 0,
                        worked_on_rest_days_count=worked_on_rest_days_count if not (is_leather or is_doctors) else 0,
                        full_shift_count=raw_row["full_shift_count"],
                        half_shift_count=raw_row["half_shift_count"],
                        total_shift_units=raw_row["total_shift_units"],
                    )
                )

        rows.sort(key=lambda row: (row.employee_name or "", row.attendance_date))
        return rows

    def build_monthly_summary_rows(
        self,
        db: Session,
        department_id: int,
        start_date: date,
        end_date: date,
        branch_id: int | None = None,
    ) -> list[ReportRow]:
        """Monthly summary builder for Reception, Leather, and Doctors departments."""
        department = db.query(Department).filter(Department.id == department_id).first() if department_id else None
        employees = self._query_department_employees(db, department_id, branch_id)
        return self._build_monthly_rows_for_employees(db, employees, start_date, end_date, department)

    def _build_monthly_rows_for_employees(
        self,
        db: Session,
        employees: list[Employee],
        start_date: date,
        end_date: date,
        department: Department | None = None,
    ) -> list[ReportRow]:
        if not employees:
            return []

        employee_ids = [employee.id for employee in employees]
        log_map = self._build_log_map(db, employee_ids, start_date, end_date)
        record_map = self._build_record_map(db, employee_ids, start_date, end_date)

        all_rows: list[ReportRow] = []
        for employee in employees:
            emp_dept = employee.department or department
            is_leather = self.is_leather_department(emp_dept)
            is_doctors = self.is_doctors_department(emp_dept)

            raw_rows: list[dict] = []
            working_days = 0
            total_hours = 0.0
            total_late = 0
            total_ot = 0.0
            total_full_shifts = 0
            total_half_shifts = 0
            total_shift_units = 0.0
            absent_days_count = 0
            weekly_rest_days_count = 0
            worked_on_rest_days_count = 0

            for current_date in self._iter_dates(start_date, end_date):
                shift_info = self._resolve_shift_info(employee, current_date) if not (is_leather or is_doctors) else None
                is_rest_day = self._is_rest_day(employee, current_date) if not (is_leather or is_doctors) else False
                record = record_map.get((employee.id, current_date))
                day_logs = log_map.get((employee.id, current_date))
                if record:
                    first_log = record.check_in_time
                    last_log = record.check_out_time
                    worked_on_rest_day = bool(record.worked_on_rest_day) if not (is_leather or is_doctors) else False
                    is_manual = bool(getattr(record, "is_manual_attendance", False) or getattr(record, "source_type", "") == "manual")
                    if is_manual and record.working_hours is not None:
                        working_hours = round(record.working_hours, 2)
                        late_minutes = record.late_minutes if not is_leather else 0
                    else:
                        effective_first_log, auto_late = self._effective_check_in_and_late(
                            first_log, emp_dept, shift_info=shift_info, is_doctors=is_doctors
                        )
                        working_hours = self._working_hours(effective_first_log, last_log)
                        late_minutes = auto_late if not is_leather else 0

                    overtime_hours = round(getattr(record, "overtime_hours", 0.0) or 0.0, 2)
                    shift_deficit_hours = round(getattr(record, "shift_deficit_hours", 0.0) or 0.0, 2)
                    status = record.status or ("present" if first_log else "absent")
                else:
                    first_log = day_logs["first"] if day_logs else None
                    last_log = day_logs["last"] if day_logs else None
                    if first_log and last_log and last_log <= first_log:
                        last_log = None

                    effective_first_log, auto_late = self._effective_check_in_and_late(
                        first_log, emp_dept, shift_info=shift_info, is_doctors=is_doctors
                    )
                    working_hours = self._working_hours(effective_first_log, last_log)
                    late_minutes = auto_late if not is_leather else 0
                    overtime_hours = 0.0
                    shift_deficit_hours = 0.0
                    worked_on_rest_day = False
                    status = "present" if first_log else "absent"

                if is_leather:
                    worked_on_rest_day = False
                    late_minutes = 0
                    overtime_hours = 0.0
                    shift_deficit_hours = 0.0
                    status = "present" if first_log else "absent"
                elif is_doctors:
                    worked_on_rest_day = False
                    shift_hours = emp_dept.shift_hours if (emp_dept and emp_dept.shift_hours) else 7
                    full_shift_hours = shift_hours * 2
                    overtime_hours = round(working_hours - full_shift_hours, 2) if working_hours > full_shift_hours else 0.0
                    shift_deficit_hours = round(shift_hours - working_hours, 2) if (0 < working_hours < shift_hours) else 0.0
                    status = "present" if first_log else "absent"
                else:
                    worked_on_rest_day = bool(first_log and is_rest_day)
                    if shift_info and last_log and shift_info.get("end_time"):
                        shift_end = datetime.combine(last_log.date(), shift_info["end_time"])
                        if last_log > shift_end:
                            overtime_hours = round((last_log - shift_end).total_seconds() / 3600, 2)
                        if last_log < shift_end and first_log:
                            shift_deficit_hours = round((shift_end - last_log).total_seconds() / 3600, 2)

                    if first_log:
                        status = "present_on_rest_day" if worked_on_rest_day else "present"
                    elif is_rest_day:
                        status = "weekly_rest"
                    else:
                        status = "absent"

                if status in ("present", "present_on_rest_day"):
                    working_days += 1
                    total_hours += working_hours
                    total_late += late_minutes
                    total_ot += overtime_hours

                if status == "present_on_rest_day":
                    worked_on_rest_days_count += 1
                elif status == "weekly_rest":
                    weekly_rest_days_count += 1
                elif status == "absent":
                    absent_days_count += 1

                # Calculate shift units & labels
                if is_doctors:
                    shift_hours = emp_dept.shift_hours if (emp_dept and emp_dept.shift_hours) else 7
                    full_shift_hours = shift_hours * 2
                    is_full = working_hours >= (full_shift_hours - 0.05)
                    is_half = not is_full and (working_hours >= (shift_hours - 0.05))
                    day_full_count = 1 if is_full else 0
                    day_half_count = 1 if is_half else 0
                    day_units = 1.0 if is_full else (0.5 if is_half else 0.0)
                    total_full_shifts += day_full_count
                    total_half_shifts += day_half_count
                    total_shift_units += day_units
                    shift_name = "شفت كامل" if is_full else ("نصف شيفت" if is_half else ("نقص في الشفت" if working_hours > 0 else None))
                    shift_type = "full_shift" if is_full else ("half_shift" if is_half else ("incomplete" if working_hours > 0 else None))
                    shift_start_time = self._format_time(emp_dept.shift_start_time) if emp_dept else None
                    shift_end_time = self._format_time(emp_dept.shift_end_time) if emp_dept else None
                elif is_leather:
                    day_full_count = 0
                    day_half_count = 0
                    day_units = 0.0
                    shift_name = None
                    shift_type = None
                    shift_start_time = None
                    shift_end_time = None
                else:
                    day_full_count = 0
                    day_half_count = 0
                    day_units = 0.0
                    shift_name = shift_info["label"] if shift_info else None
                    shift_type = shift_info["shift_type"] if shift_info else None
                    shift_start_time = self._format_time(shift_info["start_time"]) if shift_info else None
                    shift_end_time = self._format_time(shift_info["end_time"]) if shift_info else None

                raw_rows.append(
                    {
                        "current_date": current_date,
                        "shift_name": shift_name,
                        "shift_type": shift_type,
                        "shift_start_time": shift_start_time,
                        "shift_end_time": shift_end_time,
                        "first_log": first_log,
                        "last_log": last_log,
                        "working_hours": working_hours,
                        "overtime_hours": overtime_hours,
                        "shift_deficit_hours": shift_deficit_hours,
                        "late_minutes": late_minutes,
                        "status": status,
                        "worked_on_rest_day": worked_on_rest_day,
                        "full_shift_count": day_full_count,
                        "half_shift_count": day_half_count,
                        "total_shift_units": day_units,
                    }
                )

            emp_name = self._employee_full_name(employee)
            dept_name = emp_dept.name if emp_dept else None

            # Daily detail rows
            for raw_row in raw_rows:
                all_rows.append(
                    ReportRow(
                        row_kind="daily",
                        employee_code=employee.employee_code,
                        employee_name=emp_name,
                        department=dept_name,
                        job_title=employee.job_title,
                        attendance_date=raw_row["current_date"].isoformat(),
                        shift_name=raw_row["shift_name"],
                        shift_type=raw_row["shift_type"],
                        shift_start_time=raw_row["shift_start_time"],
                        shift_end_time=raw_row["shift_end_time"],
                        check_in_time=self._format_datetime(raw_row["first_log"]),
                        check_out_time=self._format_datetime(raw_row["last_log"]),
                        working_hours=raw_row["working_hours"],
                        overtime_hours=raw_row.get("overtime_hours", 0.0),
                        shift_deficit_hours=raw_row.get("shift_deficit_hours", 0.0),
                        status=raw_row["status"],
                        is_late=raw_row["late_minutes"] > 0 if not is_leather else False,
                        late_minutes=raw_row["late_minutes"] if not is_leather else 0,
                        worked_on_rest_day=raw_row["worked_on_rest_day"],
                        absent_days_count=absent_days_count if not is_leather else 0,
                        weekly_rest_days_count=weekly_rest_days_count if not (is_leather or is_doctors) else 0,
                        worked_on_rest_days_count=worked_on_rest_days_count if not (is_leather or is_doctors) else 0,
                        full_shift_count=raw_row["full_shift_count"],
                        half_shift_count=raw_row["half_shift_count"],
                        total_shift_units=raw_row["total_shift_units"],
                    )
                )

            # Summary row for this employee
            all_rows.append(
                ReportRow(
                    row_kind="summary",
                    employee_code=employee.employee_code,
                    employee_name=emp_name,
                    department=dept_name,
                    job_title=employee.job_title,
                    attendance_date="ملخص شهري",
                    check_in_time=None,
                    check_out_time=None,
                    working_hours=round(total_hours, 2),
                    status="monthly_summary",
                    is_late=False,
                    working_days_count=working_days,
                    total_late_minutes=total_late if not is_leather else 0,
                    total_overtime_hours=round(total_ot, 2) if not is_leather else 0.0,
                    worked_on_rest_days_count=worked_on_rest_days_count if not (is_leather or is_doctors) else 0,
                    weekly_rest_days_count=weekly_rest_days_count if not (is_leather or is_doctors) else 0,
                    absent_days_count=absent_days_count,
                    full_shift_count=total_full_shifts if is_doctors else 0,
                    half_shift_count=total_half_shifts if is_doctors else 0,
                    total_shift_units=round(total_shift_units, 2) if is_doctors else 0.0,
                )
            )

        all_rows.sort(key=lambda r: (
            r.employee_name or "", r.employee_code or "",
            0 if r.row_kind == "summary" else 1, r.attendance_date,
        ))
        return all_rows

    def _resolve_shift_info(self, employee: Employee, target_date: date) -> dict | None:
        if not employee or not employee.department:
            return None
            
        dept = employee.department
        grace_minutes = getattr(dept, "grace_period_minutes", None)
        if grace_minutes is None:
            if dept.shift_start_time and dept.late_start_time:
                t1 = datetime.combine(target_date, dept.shift_start_time)
                t2 = datetime.combine(target_date, dept.late_start_time)
                grace_minutes = max(0, int((t2 - t1).total_seconds() // 60))
            else:
                grace_minutes = 30
        return {
            "label": self.SHIFT_TYPE_LABELS.get("morning", "شيفت صباحي"),
            "shift_type": "morning",
            "start_time": dept.shift_start_time,
            "end_time": dept.shift_end_time,
            "grace_period_minutes": grace_minutes,
        }

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
