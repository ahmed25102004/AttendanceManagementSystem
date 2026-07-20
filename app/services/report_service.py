from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.report import ReportRow
from app.services.reception_service import ReceptionService


class ReportService:
    def __init__(self) -> None:
        self.reception_service = ReceptionService()

    def _format_time(self, value) -> str | None:
        return value.strftime("%H:%M") if value else None

    def _is_doctors_department(self, record: AttendanceRecord) -> bool:
        return bool(record.employee.department and record.employee.department.attendance_policy == "doctors_department")

    def _is_unified_department(self, department: Department | None) -> bool:
        return bool(department and (department.attendance_policy == "reception_department" or 
                                    department.attendance_policy == "workers_department" or 
                                    department.attendance_policy == "leather_department"))

    def _calculate_overtime_hours(self, record: AttendanceRecord) -> float:
        if not record.employee.department or not record.check_in_time or not record.check_out_time:
            return 0
        department = record.employee.department
        
        # For unified departments (reception, workers), calculate overtime based on department settings
        if self._is_unified_department(department):
            if not getattr(department, 'overtime_enabled', True):
                return 0
            overtime_start = datetime.combine(
                record.check_in_time.date(),
                department.overtime_start_time
            )
            if record.check_out_time <= overtime_start:
                return 0
            overtime_duration = record.check_out_time - overtime_start
            overtime_hours = overtime_duration.total_seconds() / 3600
            return round(overtime_hours, 2)
        
        # For doctors department
        if self._is_doctors_department(record):
            overtime_start = datetime.combine(
                record.check_in_time.date(),
                department.overtime_start_time
            )
            if record.check_out_time <= overtime_start:
                return 0
            overtime_duration = record.check_out_time - overtime_start
            overtime_hours = overtime_duration.total_seconds() / 3600
            return round(overtime_hours, 2)
            
        return 0

    def _resolve_shift_details(self, record: AttendanceRecord) -> tuple[str | None, str | None, str | None]:
        if self._is_doctors_department(record):
            department = record.employee.department
            if record.shift_category == "full_shift":
                return (
                    "شفت كامل",
                    self._format_time(department.full_shift_start_time),
                    self._format_time(department.full_shift_end_time),
                )
            if record.shift_category == "half_shift":
                return (
                    "نصف شفت",
                    self._format_time(department.half_shift_start_time),
                    self._format_time(department.half_shift_end_time),
                )
            if record.shift_category == "half_shift_plus_overtime":
                return (
                    "نصف شفت + اوفرتايم",
                    self._format_time(department.half_shift_start_time),
                    self._format_time(department.full_shift_end_time),
                )
            if record.shift_category == "incomplete":
                return (
                    "غير مكتمل",
                    self._format_time(department.half_shift_start_time),
                    self._format_time(department.half_shift_end_time),
                )

        return (
            record.employee.shift.name if record.employee.shift else None,
            None,
            None,
        )

    def _build_summary_rows(self, records: list[AttendanceRecord]) -> list[ReportRow]:
        summary_rows: list[ReportRow] = []
        grouped: dict[int, list[AttendanceRecord]] = {}

        for record in records:
            if self._is_doctors_department(record):
                grouped.setdefault(record.employee_id, []).append(record)

        for employee_records in grouped.values():
            first_record = employee_records[0]
            employee = first_record.employee
            full_name = " ".join(
                part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip()
            )
            full_shift_count = sum(1 for record in employee_records if record.shift_category == "full_shift")
            half_shift_count = sum(1 for record in employee_records if record.shift_category in ["half_shift", "half_shift_plus_overtime"])
            total_shift_units = sum(record.shift_units or 0 for record in employee_records)
            total_late_minutes = sum(record.late_minutes or 0 for record in employee_records)
            total_working_hours = round(sum(record.working_hours or 0 for record in employee_records), 2)
            total_overtime_hours = round(sum(getattr(record, 'overtime_hours', self._calculate_overtime_hours(record)) for record in employee_records), 2)
            total_shift_deficit = round(sum(getattr(record, 'shift_deficit_hours', 0.0) for record in employee_records), 2)

            summary_rows.append(
                ReportRow(
                    employee_code=employee.employee_code,
                    employee_name=full_name,
                    department=employee.department.name if employee.department else None,
                    job_title="ملخص الشهر",
                    attendance_date="ملخص الشهر",
                    row_kind="summary",
                    shift_name=f"كامل: {full_shift_count} | نصف: {half_shift_count} | الإجمالي: {total_shift_units:g}",
                    check_in_time=None,
                    check_out_time=None,
                    working_hours=total_working_hours,
                    overtime_hours=0,
                    shift_deficit_hours=0,
                    status="monthly_summary",
                    is_late=total_late_minutes > 0,
                    late_minutes=total_late_minutes,
                    worked_on_rest_day=False,
                    full_shift_count=full_shift_count,
                    half_shift_count=half_shift_count,
                    total_shift_units=total_shift_units,
                    total_late_minutes=total_late_minutes,
                    total_overtime_hours=total_overtime_hours,
                )
            )

        return summary_rows

    def _build_rows(self, records: list[AttendanceRecord], include_monthly_summary: bool = False) -> list[ReportRow]:
        rows: list[ReportRow] = []
        for record in records:
            full_name = " ".join(
                part.strip() for part in [record.employee.first_name, record.employee.last_name] if part and part.strip()
            )
            shift_name, shift_start_time, shift_end_time = self._resolve_shift_details(record)
            overtime_hours = getattr(record, 'overtime_hours', self._calculate_overtime_hours(record))
            shift_deficit_hours = getattr(record, 'shift_deficit_hours', 0.0)
            rows.append(
                ReportRow(
                    employee_code=record.employee.employee_code,
                    employee_name=full_name,
                    department=record.employee.department.name if record.employee.department else None,
                    job_title=record.employee.job_title,
                    attendance_date=record.attendance_date.isoformat(),
                    row_kind="daily",
                    shift_name=shift_name,
                    shift_type=record.shift_category,
                    shift_start_time=shift_start_time,
                    shift_end_time=shift_end_time,
                    check_in_time=record.check_in_time.isoformat() if record.check_in_time else None,
                    check_out_time=record.check_out_time.isoformat() if record.check_out_time else None,
                    working_hours=round(record.working_hours, 2),
                    overtime_hours=overtime_hours,
                    shift_deficit_hours=shift_deficit_hours,
                    status=record.status,
                    is_late=record.is_late,
                    late_minutes=record.late_minutes,
                    worked_on_rest_day=record.worked_on_rest_day,
                    total_shift_units=record.shift_units or 0,
                )
            )
        if include_monthly_summary:
            rows.extend(self._build_summary_rows(records))
        return rows

    def _use_reception_rows(self, db: Session, department_id: int | None) -> bool:
        if not department_id:
            return False
        department = db.query(Department).filter(Department.id == department_id).first()
        return self._is_unified_department(department)

    def daily_report(self, db: Session, report_date: date, branch_id: int | None = None, department_id: int | None = None) -> list[ReportRow]:
        if self._use_reception_rows(db, department_id):
            return self.reception_service.build_report_rows(db, department_id, report_date, report_date, branch_id)

        records = (
            db.query(AttendanceRecord)
            .options(
                joinedload(AttendanceRecord.employee).joinedload(Employee.department),
                joinedload(AttendanceRecord.employee).joinedload(Employee.shift),
            )
            .filter(AttendanceRecord.attendance_date == report_date)
        )
        if branch_id or department_id:
            records = records.join(Employee)
            if branch_id:
                records = records.filter(Employee.branch_id == branch_id)
            if department_id:
                records = records.filter(Employee.department_id == department_id)
        records = records.order_by(AttendanceRecord.id.desc()).all()
        return self._build_rows(records)

    def weekly_report(self, db: Session, report_date: date, branch_id: int | None = None, department_id: int | None = None) -> list[ReportRow]:
        week_start = report_date - timedelta(days=report_date.weekday())
        week_end = week_start + timedelta(days=7)
        if self._use_reception_rows(db, department_id):
            return self.reception_service.build_report_rows(db, department_id, week_start, week_end - timedelta(days=1), branch_id)

        records = (
            db.query(AttendanceRecord)
            .options(
                joinedload(AttendanceRecord.employee).joinedload(Employee.department),
                joinedload(AttendanceRecord.employee).joinedload(Employee.shift),
            )
            .filter(AttendanceRecord.attendance_date >= week_start, AttendanceRecord.attendance_date < week_end)
        )
        if branch_id or department_id:
            records = records.join(Employee)
            if branch_id:
                records = records.filter(Employee.branch_id == branch_id)
            if department_id:
                records = records.filter(Employee.department_id == department_id)
        records = records.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id.desc()).all()
        return self._build_rows(records)

    def monthly_report(self, db: Session, month: str, branch_id: int | None = None, department_id: int | None = None) -> list[ReportRow]:
        month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1)

        if self._use_reception_rows(db, department_id):
            return self.reception_service.build_report_rows(db, department_id, month_start, month_end - timedelta(days=1), branch_id)

        records = (
            db.query(AttendanceRecord)
            .options(
                joinedload(AttendanceRecord.employee).joinedload(Employee.department),
                joinedload(AttendanceRecord.employee).joinedload(Employee.shift),
            )
            .filter(AttendanceRecord.attendance_date >= month_start, AttendanceRecord.attendance_date < month_end)
        )
        if branch_id or department_id:
            records = records.join(Employee)
            if branch_id:
                records = records.filter(Employee.branch_id == branch_id)
            if department_id:
                records = records.filter(Employee.department_id == department_id)
        records = records.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id.desc()).all()
        return self._build_rows(records, include_monthly_summary=True)
