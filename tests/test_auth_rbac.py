import unittest

from pydantic import ValidationError

from app.schemas.employee import EmployeeCreate


class AuthRbacTests(unittest.TestCase):
    def test_employee_create_rejects_non_supported_roles(self) -> None:
        with self.assertRaises(ValidationError):
            EmployeeCreate(
                employee_code="EMP001",
                full_name="Ahmed Mohamed",
                phone="01000000000",
                address="Cairo",
                job_title="Developer",
                hire_date="2024-01-01",
                role="manager",
            )

    def test_employee_create_accepts_admin_role(self) -> None:
        payload = EmployeeCreate(
            employee_code="EMP002",
            full_name="Sara Ali",
            phone="01000000001",
            address="Cairo",
            job_title="Analyst",
            hire_date="2024-01-02",
            role="admin",
        )

        self.assertEqual(payload.role, "admin")


if __name__ == "__main__":
    unittest.main()
