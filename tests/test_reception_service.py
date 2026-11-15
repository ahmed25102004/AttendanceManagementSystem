import unittest
from datetime import date, datetime, time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.branch import Branch
from app.models.department import Department
from app.models.device import Device
from app.models.employee import Employee
from app.services.reception_service import ReceptionService
from app.services.report_service import ReportService


class ReceptionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def test_build_report_rows_uses_first_and_last_logs_and_marks_rest_work(self) -> None:
        session = self.Session()
        try:
            branch = Branch(name="Main Branch")
            department = Department(
                name="قسم الريسبشن",
                attendance_policy="reception_department",
                shift_start_time=time(7, 30),
                shift_end_time=time(14, 30),
                grace_period_minutes=15,
                late_start_time=time(7, 45),
            )
            session.add_all([branch, department])
            session.flush()

            device = Device(
                device_name="ZK-1",
                device_code="DEV001",
                branch_id=branch.id,
            )
            employee = Employee(
                branch_id=branch.id,
                employee_code="EMP001",
                first_name="Ahmed",
                last_name="Ali",
                email="emp001@example.com",
                phone="01000000000",
                address="Cairo",
                job_title="Receptionist",
                hire_date=date(2024, 1, 1),
                is_active=True,
                department_id=department.id,
                weekly_rest_day="friday",
            )
            session.add_all([device, employee])
            session.flush()

            session.add_all(
                [
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 13, 7, 50),
                        attendance_type="check_in",
                    ),
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 13, 12, 0),
                        attendance_type="check_out",
                    ),
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 13, 14, 40),
                        attendance_type="check_out",
                    ),
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 17, 8, 0),
                        attendance_type="check_in",
                    ),
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 17, 12, 0),
                        attendance_type="check_out",
                    ),
                ]
            )
            session.commit()

            rows = ReceptionService().build_report_rows(
                session,
                department.id,
                start_date=date(2026, 7, 13),
                end_date=date(2026, 7, 17),
                branch_id=branch.id,
            )

            self.assertEqual(len(rows), 5)

            monday_row = next(row for row in rows if row.attendance_date == "2026-07-13")
            tuesday_row = next(row for row in rows if row.attendance_date == "2026-07-14")
            friday_row = next(row for row in rows if row.attendance_date == "2026-07-17")

            self.assertEqual(monday_row.check_in_time, "2026-07-13T07:50:00")
            self.assertEqual(monday_row.check_out_time, "2026-07-13T14:40:00")
            self.assertEqual(monday_row.late_minutes, 20)
            self.assertEqual(monday_row.status, "present")

            self.assertEqual(tuesday_row.status, "absent")
            self.assertEqual(tuesday_row.absent_days_count, 3)

            self.assertEqual(friday_row.status, "present_on_rest_day")
            self.assertTrue(friday_row.worked_on_rest_day)
            self.assertEqual(friday_row.worked_on_rest_days_count, 1)
        finally:
            session.close()

    def test_build_report_rows_prefers_manual_attendance_record_over_logs(self) -> None:
        session = self.Session()
        try:
            branch = Branch(name="Reception Branch")
            department = Department(
                name="قسم الريسبشن",
                attendance_policy="reception_department",
                shift_start_time=time(14, 0),
                shift_end_time=time(21, 30),
                grace_period_minutes=15,
                late_start_time=time(14, 15),
            )
            session.add_all([branch, department])
            session.flush()

            device = Device(
                device_name="ZK-2",
                device_code="DEV002",
                branch_id=branch.id,
            )
            employee = Employee(
                branch_id=branch.id,
                employee_code="EMP002",
                first_name="Sara",
                last_name="Hassan",
                email="emp002@example.com",
                phone="01000000001",
                address="Giza",
                job_title="Receptionist",
                hire_date=date(2024, 1, 1),
                is_active=True,
                department_id=department.id,
                weekly_rest_day="saturday",
            )
            session.add_all([device, employee])
            session.flush()

            session.add_all(
                [
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 15, 14, 30),
                        attendance_type="check_in",
                    ),
                    AttendanceLog(
                        employee_id=employee.id,
                        branch_id=branch.id,
                        device_id=device.id,
                        employee_code=employee.employee_code,
                        check_time=datetime(2026, 7, 15, 21, 0),
                        attendance_type="check_out",
                    ),
                    AttendanceRecord(
                        employee_id=employee.id,
                        attendance_date=date(2026, 7, 15),
                        check_in_time=datetime(2026, 7, 15, 14, 5),
                        check_out_time=datetime(2026, 7, 15, 21, 25),
                        working_hours=7.33,
                        is_late=False,
                        late_minutes=0,
                        status="present",
                        source_type="manual",
                    ),
                ]
            )
            session.commit()

            rows = ReceptionService().build_report_rows(
                session,
                department.id,
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 15),
                branch_id=branch.id,
            )

            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.check_in_time, "2026-07-15T14:05:00")
            self.assertEqual(row.check_out_time, "2026-07-15T21:25:00")
            self.assertEqual(row.late_minutes, 0)
            self.assertEqual(row.working_hours, 7.33)
        finally:
            session.close()

    def test_doctors_grace_period_and_full_shift_calculation(self) -> None:
        session = self.Session()
        try:
            branch = Branch(name="Doctors Branch")
            department = Department(
                name="الدكاتره",
                attendance_policy="doctors_department",
                shift_start_time=time(8, 0),
                shift_end_time=time(15, 0),
                shift_hours=7,
                late_start_time=time(8, 15),
                grace_period_minutes=15,
                evening_shift_start_time=time(15, 0),
                evening_shift_end_time=time(22, 0),
                evening_shift_hours=7,
                evening_shift_late_start_time=time(15, 15),
            )
            session.add_all([branch, department])
            session.flush()

            device = Device(
                device_name="ZK-DOC",
                device_code="DEV-DOC",
                branch_id=branch.id,
            )
            doctor = Employee(
                branch_id=branch.id,
                employee_code="DOC001",
                first_name="Alaa",
                last_name="Gamal",
                email="doc001@example.com",
                phone="01011111111",
                job_title="Doctor",
                hire_date=date(2024, 1, 1),
                is_active=True,
                department_id=department.id,
            )
            session.add_all([device, doctor])
            session.flush()

            # Day 1 (Nov 7): Arrives at 08:05 (within 15 min grace of 08:00), leaves at 22:00
            # Must count as full 14 hours (شفت كامل), 0 late minutes, 0 deduction!
            session.add_all([
                AttendanceLog(
                    employee_id=doctor.id,
                    branch_id=branch.id,
                    device_id=device.id,
                    employee_code=doctor.employee_code,
                    check_time=datetime(2026, 11, 7, 8, 5),
                    attendance_type="check_in",
                ),
                AttendanceLog(
                    employee_id=doctor.id,
                    branch_id=branch.id,
                    device_id=device.id,
                    employee_code=doctor.employee_code,
                    check_time=datetime(2026, 11, 7, 22, 0),
                    attendance_type="check_out",
                ),
                # Day 2 (Nov 5): Arrives at 15:16 for evening shift (starts 15:00, grace 15:15), leaves at 22:17
                # Late minutes must be 1 minute (15:16 - 15:15), NOT 7 hours!
                AttendanceLog(
                    employee_id=doctor.id,
                    branch_id=branch.id,
                    device_id=device.id,
                    employee_code=doctor.employee_code,
                    check_time=datetime(2026, 11, 5, 15, 16),
                    attendance_type="check_in",
                ),
                AttendanceLog(
                    employee_id=doctor.id,
                    branch_id=branch.id,
                    device_id=device.id,
                    employee_code=doctor.employee_code,
                    check_time=datetime(2026, 11, 5, 22, 17),
                    attendance_type="check_out",
                ),
            ])
            session.commit()

            rows = ReceptionService().build_report_rows(
                session,
                department_id=department.id,
                start_date=date(2026, 11, 5),
                end_date=date(2026, 11, 7),
                branch_id=branch.id,
            )

            nov_7_row = next(r for r in rows if r.attendance_date == "2026-11-07" and r.row_kind != "summary")
            self.assertEqual(nov_7_row.shift_name, "شفت كامل")
            self.assertEqual(nov_7_row.full_shift_count, 1)
            self.assertEqual(nov_7_row.total_shift_units, 1.0)
            self.assertEqual(nov_7_row.working_hours, 14.0)
            self.assertEqual(nov_7_row.late_minutes, 0)
            self.assertEqual(nov_7_row.shift_deficit_hours, 0.0)

            nov_5_row = next(r for r in rows if r.attendance_date == "2026-11-05" and r.row_kind != "summary")
            self.assertEqual(nov_5_row.shift_name, "نصف شيفت")
            self.assertEqual(nov_5_row.half_shift_count, 1)
            self.assertEqual(nov_5_row.total_shift_units, 0.5)
            self.assertEqual(nov_5_row.late_minutes, 1)

            # Test ReportService.custom_range_report produces identical correct doctor shift units & hours
            range_rows = ReportService().custom_range_report(
                session,
                start_date=date(2026, 11, 5),
                end_date=date(2026, 11, 7),
                department_id=department.id,
                branch_id=branch.id,
            )
            r_nov_7 = next(r for r in range_rows if r.attendance_date == "2026-11-07" and r.row_kind != "summary")
            self.assertEqual(r_nov_7.shift_name, "شفت كامل")
            self.assertEqual(r_nov_7.full_shift_count, 1)
            self.assertEqual(r_nov_7.total_shift_units, 1.0)
            self.assertEqual(r_nov_7.working_hours, 14.0)
            self.assertEqual(r_nov_7.late_minutes, 0)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
