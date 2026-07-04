import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.user import User
from app.services.employee_service import EmployeeService


class EmployeeServiceDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def test_delete_employee_removes_attendance_and_user_records(self) -> None:
        session = self.Session()
        try:
            employee = Employee(
                employee_code="EMP001",
                first_name="Ahmed",
                last_name="",
                email="ahmed@employee.local",
                phone="01000000000",
                address="Cairo",
                job_title="Developer",
                hire_date=date(2024, 1, 1),
                is_active=True,
                department_id=None,
            )
            session.add(employee)
            session.flush()

            session.add(
                AttendanceRecord(
                    employee_id=employee.id,
                    attendance_date=date(2024, 1, 2),
                    status="present",
                )
            )
            session.add(
                User(
                    username="emp_emp001",
                    password_hash="hash",
                    full_name="Ahmed",
                    role="employee",
                    is_active=True,
                    employee_id=employee.id,
                )
            )
            session.commit()

            EmployeeService().delete(session, employee.id)

            self.assertIsNone(session.query(Employee).filter(Employee.id == employee.id).first())
            self.assertEqual(session.query(AttendanceRecord).filter(AttendanceRecord.employee_id == employee.id).count(), 0)
            self.assertEqual(session.query(User).filter(User.employee_id == employee.id).count(), 0)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
