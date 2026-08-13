from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.report import ReportRow
from app.services.reception_service import ReceptionService
from app.services.workers_service import WorkersService


class ReportService:
    def __init__(self) -> None:
        self.reception_service = ReceptionService()
        self.workers_service = WorkersService()

    def _format_time(self, value) -> str | None:
        return value.strftime("%H:%M") if value else None

    def _format_datetime(self, value) -> str | None:
        return value.isoformat() if value else None

    def _employee_full_name(self, employee: Employee) -> str:
        return " ".join(part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip())

    def _week_range(self, any_day_in_week: date) -> tuple[date, date]:
        start = any_day_in_week - timedelta(days=any_day_in_week.weekday())
        end = start + timedelta(days=6)
        return start, end

    def _month_range(self, month_str: str) -> tuple[date, date]:
        year, month = (int(x) for x in month_str.split("-"))
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)
        return start, end

    def _is_workers_department(self, department: Department | None) -> bool:
        return bool(department and department.attendance_policy == "workers_department")

    def _is_reception_family_department(self, department: Department | None) -> bool:
        return bool(department and (department.attendance_policy == "reception_department" or
                                    department.attendance_policy == "leather_department"))

    def _normalize_shift_category(self, shift_category: str | None) -> str | None:
        mapping = {
            "شفت كامل": "full_shift",
            "نصف شيفت": "half_shift",
            "نصف شيفت + اوفرتايم": "half_shift_plus_overtime",
            "نقص في الشفت": "incomplete",
            "call_center_shift_1": "shift_1",
            "call_center_shift_2": "shift_2",
            "workers_shift_1": "shift_1",
            "workers_shift_2": "shift_2",
        }
        return mapping.get(shift_category, shift_category)

    def _resolve_shift_details(self, record: AttendanceRecord) -> tuple[str | None, str | None, str | None]:
        department = record.employee.department if record.employee else None
        if not department:
            return (None, None, None)

        if department.attendance_policy == "call_center_department":
            if record.shift_category == "call_center_shift_1":
                return (
                    "الشيفت الأول",
                    self._format_time(department.shift_start_time),
                    self._format_time(department.shift_end_time),
                )
            if record.shift_category == "call_center_shift_2":
                return (
                    "الشيفت الثاني",
                    self._format_time(department.evening_shift_start_time),
                    self._format_time(department.evening_shift_end_time),
                )
            return ("غير محدد", None, None)

        if department.attendance_policy == "workers_department":
            if record.shift_category == "workers_shift_1":
                return (
                    "الشيفت الأول",
                    self._format_time(department.shift_start_time),
                    self._format_time(department.shift_end_time),
                )
            if record.shift_category == "workers_shift_2":
                return (
                    "الشيفت الثاني",
                    self._format_time(department.evening_shift_start_time),
                    self._format_time(department.evening_shift_end_time),
                )
            return (None, None, None)

        if department.attendance_policy == "doctors_department":
            shift_label_map = {
                "full_shift": "شفت كامل",
                "half_shift": "نصف شيفت",
                "incomplete": "نقص في الشفت",
            }
            label = shift_label_map.get(self._normalize_shift_category(record.shift_category) or "", None)
            return (
                label,
                self._format_time(department.shift_start_time),
                self._format_time(department.shift_end_time),
            )

        return (None, None, None)

    def _build_rows_from_records(
        self,
        records: Iterable[AttendanceRecord],
        include_monthly_summary: bool = False,
    ) -> list[ReportRow]:
        """Generic row builder for departments that use AttendanceRecord data directly."""
        rows: list[ReportRow] = []
        summaries_by_employee: dict[int, dict] = {}

        for record in records:
            if not record.employee:
                continue

            employee = record.employee
            department = employee.department
            shift_name, shift_start, shift_end = self._resolve_shift_details(record)

            rows.append(
                ReportRow(
                    employee_code=employee.employee_code,
                    employee_name=self._employee_full_name(employee),
                    department=department.name if department else None,
                    job_title=employee.job_title,
                    attendance_date=record.attendance_date.isoformat(),
                    shift_name=shift_name,
                    shift_type=self._normalize_shift_category(record.shift_category),
                    shift_start_time=shift_start,
                    shift_end_time=shift_end,
                    check_in_time=self._format_datetime(record.check_in_time),
                    check_out_time=self._format_datetime(record.check_out_time),
                    working_hours=round(record.working_hours or 0.0, 2),
                    overtime_hours=round(getattr(record, "overtime_hours", 0.0) or 0.0, 2),
                    shift_deficit_hours=round(getattr(record, "shift_deficit_hours", 0.0) or 0.0, 2),
                    status=record.status or "absent",
                    is_late=bool(record.is_late),
                    late_minutes=record.late_minutes or 0,
                    worked_on_rest_day=bool(record.worked_on_rest_day),
                    full_shift_count=1 if self._normalize_shift_category(record.shift_category) == "full_shift" else 0,
                    half_shift_count=1 if self._normalize_shift_category(record.shift_category) == "half_shift" else 0,
                    total_shift_units=record.shift_units or 0.0,
                    total_late_minutes=record.late_minutes or 0,
                    total_overtime_hours=round(getattr(record, "overtime_hours", 0.0) or 0.0, 2),
                )
            )

            if include_monthly_summary:
                key = employee.id
                summary = summaries_by_employee.setdefault(
                    key,
                    {
                        "employee_code": employee.employee_code,
                        "employee_name": self._employee_full_name(employee),
                        "department_name": department.name if department else None,
                        "job_title": employee.job_title,
                        "absent_days_count": 0,
                        "weekly_rest_days_count": 0,
                        "worked_on_rest_days_count": 0,
                        "full_shift_count": 0,
                        "half_shift_count": 0,
                        "shift_1_count": 0,
                        "shift_2_count": 0,
                        "total_shift_units": 0.0,
                        "total_late_minutes": 0,
                        "total_overtime_hours": 0.0,
                    },
                )
                status = record.status or "absent"
                if status == "absent":
                    summary["absent_days_count"] += 1
                elif status == "weekly_rest":
                    summary["weekly_rest_days_count"] += 1
                if record.worked_on_rest_day:
                    summary["worked_on_rest_days_count"] += 1
                shift_norm = self._normalize_shift_category(record.shift_category)
                if shift_norm == "full_shift":
                    summary["full_shift_count"] += 1
                elif shift_norm == "half_shift":
                    summary["half_shift_count"] += 1
                elif shift_norm == "shift_1":
                    summary["shift_1_count"] += 1
                elif shift_norm == "shift_2":
                    summary["shift_2_count"] += 1
                summary["total_shift_units"] += record.shift_units or 0.0
                summary["total_late_minutes"] += record.late_minutes or 0
                summary["total_overtime_hours"] += round(getattr(record, "overtime_hours", 0.0) or 0.0, 2)

        if include_monthly_summary and summaries_by_employee:
            for summary in summaries_by_employee.values():
                rows.append(
                    ReportRow(
                        row_kind="summary",
                        employee_code=summary["employee_code"],
                        employee_name=summary["employee_name"],
                        department=summary["department_name"],
                        job_title=summary["job_title"],
                        attendance_date="ملخص شهري",
                        working_hours=0.0,
                        status="monthly_summary",
                        is_late=False,
                        absent_days_count=summary["absent_days_count"],
                        weekly_rest_days_count=summary["weekly_rest_days_count"],
                        worked_on_rest_days_count=summary["worked_on_rest_days_count"],
                        full_shift_count=summary["full_shift_count"],
                        half_shift_count=summary["half_shift_count"],
                        shift_1_count=summary["shift_1_count"],
                        shift_2_count=summary["shift_2_count"],
                        total_shift_units=round(summary["total_shift_units"], 2),
                        total_late_minutes=summary["total_late_minutes"],
                        total_overtime_hours=round(summary["total_overtime_hours"], 2),
                    )
                )

        rows.sort(key=lambda r: (r.attendance_date, r.employee_name or ""))
        return rows

    def _query_records(
        self,
        db: Session,
        start_date: date,
        end_date: date,
        branch_id: int | None,
        department_id: int | None,
    ) -> list[AttendanceRecord]:
        query = (
            db.query(AttendanceRecord)
            .options(
                joinedload(AttendanceRecord.employee).joinedload(Employee.department),
            )
            .filter(
                AttendanceRecord.attendance_date >= start_date,
                AttendanceRecord.attendance_date <= end_date,
            )
        )
        if branch_id or department_id:
            query = query.join(Employee)
            if branch_id:
                query = query.filter(Employee.branch_id == branch_id)
            if department_id:
                query = query.filter(Employee.department_id == department_id)
        return query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id.desc()).all()

    def _resolve_target_department(
        self,
        db: Session,
        department_id: int | None,
    ) -> Department | None:
        if not department_id:
            return None
        return db.query(Department).filter(Department.id == department_id).first()

    def daily_report(
        self,
        db: Session,
        report_date: date,
        branch_id: int | None,
        department_id: int | None,
    ) -> list[ReportRow]:
        target_department = self._resolve_target_department(db, department_id)

        # Workers: use dedicated workers service with per-shift logic
        if department_id and self._is_workers_department(target_department):
            return self.workers_service.build_report_rows(
                db, department_id, report_date, report_date, branch_id
            )

        # Reception / Leather: use dedicated reception service
        if department_id and self._is_reception_family_department(target_department):
            return self.reception_service.build_report_rows(
                db, department_id, report_date, report_date, branch_id
            )

        # Generic departments: build from attendance records
        records = self._query_records(db, report_date, report_date, branch_id, department_id)
        return self._build_rows_from_records(records)

    def weekly_report(
        self,
        db: Session,
        report_date: date,
        branch_id: int | None,
        department_id: int | None,
    ) -> list[ReportRow]:
        start_date, end_date = self._week_range(report_date)
        target_department = self._resolve_target_department(db, department_id)

        if department_id and self._is_workers_department(target_department):
            return self.workers_service.build_report_rows(
                db, department_id, start_date, end_date, branch_id
            )

        if department_id and self._is_reception_family_department(target_department):
            return self.reception_service.build_report_rows(
                db, department_id, start_date, end_date, branch_id
            )

        records = self._query_records(db, start_date, end_date, branch_id, department_id)
        return self._build_rows_from_records(records)

    def monthly_report(
        self,
        db: Session,
        month: str,
        branch_id: int | None,
        department_id: int | None,
    ) -> list[ReportRow]:
        start_date, end_date = self._month_range(month)
        target_department = self._resolve_target_department(db, department_id)

        if department_id and self._is_workers_department(target_department):
            return self.workers_service.build_report_rows(
                db, department_id, start_date, end_date, branch_id
            )

        if department_id and self._is_reception_family_department(target_department):
            return self.reception_service.build_report_rows(
                db, department_id, start_date, end_date, branch_id
            )

        records = self._query_records(db, start_date, end_date, branch_id, department_id)
        return self._build_rows_from_records(records, include_monthly_summary=True)
