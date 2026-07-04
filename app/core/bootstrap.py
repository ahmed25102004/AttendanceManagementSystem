from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.security import security_manager
from app.models.company_setting import CompanySetting
from app.models.employee import Employee
from app.models.user import User


settings = get_settings()


def _employee_username(employee_id: int) -> str:
    return f"emp_{employee_id}"


def ensure_schema_updates() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "users" in tables:
            user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
            if "employee_id" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN employee_id INTEGER"))

        if "company_settings" in tables:
            setting_columns = {column["name"] for column in inspect(engine).get_columns("company_settings")}
            statements = {
                "workplace_latitude": "ALTER TABLE company_settings ADD COLUMN workplace_latitude DOUBLE PRECISION",
                "workplace_longitude": "ALTER TABLE company_settings ADD COLUMN workplace_longitude DOUBLE PRECISION",
                "workplace_radius_meters": "ALTER TABLE company_settings ADD COLUMN workplace_radius_meters INTEGER NOT NULL DEFAULT 150",
                "allowed_ip_ranges": "ALTER TABLE company_settings ADD COLUMN allowed_ip_ranges VARCHAR(500) NOT NULL DEFAULT ''",
                "enforce_geofence": "ALTER TABLE company_settings ADD COLUMN enforce_geofence BOOLEAN NOT NULL DEFAULT FALSE",
                "enforce_ip_check": "ALTER TABLE company_settings ADD COLUMN enforce_ip_check BOOLEAN NOT NULL DEFAULT FALSE",
                "face_match_threshold": "ALTER TABLE company_settings ADD COLUMN face_match_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.6",
                "check_in_open_time": "ALTER TABLE company_settings ADD COLUMN check_in_open_time TIME NOT NULL DEFAULT '08:00:00'",
                "check_in_close_time": "ALTER TABLE company_settings ADD COLUMN check_in_close_time TIME NOT NULL DEFAULT '11:00:00'",
                "check_out_open_time": "ALTER TABLE company_settings ADD COLUMN check_out_open_time TIME NOT NULL DEFAULT '16:00:00'",
                "check_out_close_time": "ALTER TABLE company_settings ADD COLUMN check_out_close_time TIME NOT NULL DEFAULT '22:00:00'",
                "auto_backup_enabled": "ALTER TABLE company_settings ADD COLUMN auto_backup_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                "auto_backup_time": "ALTER TABLE company_settings ADD COLUMN auto_backup_time TIME NOT NULL DEFAULT '02:00:00'",
                "auto_backup_retention_days": "ALTER TABLE company_settings ADD COLUMN auto_backup_retention_days INTEGER NOT NULL DEFAULT 30",
            }
            for column_name, statement in statements.items():
                if column_name not in setting_columns:
                    connection.execute(text(statement))

        if "employees" in tables:
            employee_columns = {column["name"] for column in inspect(engine).get_columns("employees")}
            statements = {
                "face_images": "ALTER TABLE employees ADD COLUMN face_images JSON",
                "face_descriptor": "ALTER TABLE employees ADD COLUMN face_descriptor JSON",
                "face_registered_at": "ALTER TABLE employees ADD COLUMN face_registered_at TIMESTAMP",
                "face_verification_enabled": "ALTER TABLE employees ADD COLUMN face_verification_enabled BOOLEAN NOT NULL DEFAULT TRUE",
                "annual_leave_balance": "ALTER TABLE employees ADD COLUMN annual_leave_balance INTEGER NOT NULL DEFAULT 20",
                "sick_leave_balance": "ALTER TABLE employees ADD COLUMN sick_leave_balance INTEGER NOT NULL DEFAULT 10",
                "employment_type": "ALTER TABLE employees ADD COLUMN employment_type VARCHAR(50) NOT NULL DEFAULT 'full_time'",
                "shift_id": "ALTER TABLE employees ADD COLUMN shift_id INTEGER",
            }
            for column_name, statement in statements.items():
                if column_name not in employee_columns:
                    connection.execute(text(statement))


def _sync_employee_user(db: Session, employee: Employee) -> None:
    username = _employee_username(employee.id)
    full_name = " ".join(part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip())
    user = db.query(User).filter(User.employee_id == employee.id).first()
    if not user:
        user = User(
            username=username,
            password_hash=security_manager.hash_password(f"emp_{employee.id}@123"),
            full_name=full_name,
            role="employee",
            is_active=employee.is_active,
            employee_id=employee.id,
        )
        db.add(user)
        return

    user.full_name = full_name
    user.is_active = employee.is_active


def bootstrap_defaults() -> None:
    ensure_schema_updates()
    db: Session = SessionLocal()
    try:
        company_settings = db.query(CompanySetting).first()
        if not company_settings:
            company_settings = CompanySetting(company_name=settings.company_name)
            db.add(company_settings)

        admin = db.query(User).filter(User.username == settings.admin_username).first()
        if not admin:
            admin = User(
                username=settings.admin_username,
                password_hash=security_manager.hash_password(settings.admin_password),
                full_name="System Administrator",
                role="admin",
                is_active=True,
            )
            db.add(admin)

        employees = db.query(Employee).all()
        for employee in employees:
            _sync_employee_user(db, employee)

        db.commit()
    finally:
        db.close()
