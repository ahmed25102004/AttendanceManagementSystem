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
from app.models.shift import Shift
from app.services.reception_service import ReceptionService


class ReceptionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def test_build_report_rows_uses_first_and_last_logs_and_marks_rest_work(self) -> None:
        session = self.Session()
        try:
            branch = Branch(name="Main Branch")
            department = Department(name="قسم الريسبشن", attendance_policy="reception_department")
            shift = Shift(
                name="صباحي",
                start_time=time(7, 30),
                end_time=time(14, 30),
                grace_period_minutes=15,
            )
            session.add_all([branch, department, shift])
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
                shift_id=shift.id,
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
            department = Department(name="قسم الريسبشن", attendance_policy="reception_department")
            shift = Shift(
                name="مسائي",
                start_time=time(14, 0),
                end_time=time(21, 30),
                grace_period_minutes=15,
            )
            session.add_all([branch, department, shift])
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
                shift_id=shift.id,
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


if __name__ == "__main__":
    unittest.main()
