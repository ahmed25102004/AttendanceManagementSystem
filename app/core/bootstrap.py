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
        # Create devices table if not exists
        if "devices" not in tables:
            connection.execute(text("""
                CREATE TABLE devices (
                    id SERIAL PRIMARY KEY,
                    device_name VARCHAR(100) NOT NULL,
                    device_code VARCHAR(50) NOT NULL UNIQUE,
                    serial_number VARCHAR(100),
                    branch_id INTEGER NOT NULL REFERENCES branches(id),
                    ip_address VARCHAR(45),
                    port INTEGER,
                    protocol VARCHAR(20) NOT NULL DEFAULT 'ADMS',
                    firmware_version VARCHAR(50),
                    status VARCHAR(20) NOT NULL DEFAULT 'Offline',
                    last_sync TIMESTAMP,
                    last_seen TIMESTAMP,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_devices_device_code ON devices(device_code)"))
            connection.execute(text("CREATE INDEX idx_devices_branch_id ON devices(branch_id)"))
        else:
            # If devices table already exists, make sure all columns are there
            device_columns = {column["name"] for column in inspect(engine).get_columns("devices")}
            device_statements = {
                "device_name": "ALTER TABLE devices ADD COLUMN device_name VARCHAR(100) NOT NULL",
                "device_code": "ALTER TABLE devices ADD COLUMN device_code VARCHAR(50) NOT NULL UNIQUE",
                "serial_number": "ALTER TABLE devices ADD COLUMN serial_number VARCHAR(100)",
                "branch_id": "ALTER TABLE devices ADD COLUMN branch_id INTEGER NOT NULL REFERENCES branches(id)",
                "ip_address": "ALTER TABLE devices ADD COLUMN ip_address VARCHAR(45)",
                "port": "ALTER TABLE devices ADD COLUMN port INTEGER",
                "protocol": "ALTER TABLE devices ADD COLUMN protocol VARCHAR(20) NOT NULL DEFAULT 'ADMS'",
                "firmware_version": "ALTER TABLE devices ADD COLUMN firmware_version VARCHAR(50)",
                "status": "ALTER TABLE devices ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Offline'",
                "last_sync": "ALTER TABLE devices ADD COLUMN last_sync TIMESTAMP",
                "last_seen": "ALTER TABLE devices ADD COLUMN last_seen TIMESTAMP",
                "is_active": "ALTER TABLE devices ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE",
                "created_at": "ALTER TABLE devices ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT NOW()",
                "updated_at": "ALTER TABLE devices ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
            }
            for col_name, col_stmt in device_statements.items():
                if col_name not in device_columns:
                    try:
                        connection.execute(text(col_stmt))
                    except:
                        pass

        # Create attendance_logs table if not exists
        if "attendance_logs" not in tables:
            connection.execute(text("""
                CREATE TABLE attendance_logs (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER REFERENCES employees(id),
                    branch_id INTEGER NOT NULL REFERENCES branches(id),
                    device_id INTEGER NOT NULL REFERENCES devices(id),
                    employee_code VARCHAR(30) NOT NULL,
                    check_time TIMESTAMP NOT NULL,
                    attendance_type VARCHAR(20),
                    verify_type VARCHAR(20),
                    source VARCHAR(30) NOT NULL DEFAULT 'ZKTeco',
                    raw_data JSON,
                    record_id VARCHAR(50),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_attendance_logs_employee_id ON attendance_logs(employee_id)"))
            connection.execute(text("CREATE INDEX idx_attendance_logs_branch_id ON attendance_logs(branch_id)"))
            connection.execute(text("CREATE INDEX idx_attendance_logs_device_id ON attendance_logs(device_id)"))
            connection.execute(text("CREATE INDEX idx_attendance_logs_employee_code ON attendance_logs(employee_code)"))
            connection.execute(text("CREATE INDEX idx_attendance_logs_check_time ON attendance_logs(check_time)"))
            connection.execute(text("CREATE INDEX idx_attendance_logs_record_id ON attendance_logs(record_id)"))

        # Create branches table if not exists
        if "branches" not in tables:
            connection.execute(text("""
                CREATE TABLE branches (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))
            connection.execute(text("CREATE INDEX idx_branches_name ON branches(name)"))
        else:
            # If branches table already exists, add missing columns
            branch_columns = {column["name"] for column in inspect(engine).get_columns("branches")}
            branch_statements = {
                "description": "ALTER TABLE branches ADD COLUMN description VARCHAR(255)",
                "is_active": "ALTER TABLE branches ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
            }
            for col_name, col_stmt in branch_statements.items():
                if col_name not in branch_columns:
                    try:
                        connection.execute(text(col_stmt))
                    except:
                        pass

        # Create shifts table if not exists
        if "shifts" not in tables:
            connection.execute(text("""
                CREATE TABLE shifts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    grace_period_minutes INTEGER NOT NULL DEFAULT 15,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))

        # Create leaves table if not exists
        if "leaves" not in tables:
            connection.execute(text("""
                CREATE TABLE leaves (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    type VARCHAR(50) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    reason TEXT,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_leaves_employee_id ON leaves(employee_id)"))

        # Create tasks table if not exists
        if "tasks" not in tables:
            connection.execute(text("""
                CREATE TABLE tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    assigned_to INTEGER NOT NULL REFERENCES employees(id),
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    priority VARCHAR(50) NOT NULL DEFAULT 'medium',
                    due_date DATE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to)"))
            connection.execute(text("CREATE INDEX idx_tasks_created_by ON tasks(created_by)"))

        # Create notifications table if not exists
        if "notifications" not in tables:
            connection.execute(text("""
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_notifications_user_id ON notifications(user_id)"))

        # Create employee_documents table if not exists
        if "employee_documents" not in tables:
            connection.execute(text("""
                CREATE TABLE employee_documents (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    file_type VARCHAR(100) NOT NULL,
                    notes TEXT,
                    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            connection.execute(text("CREATE INDEX idx_employee_documents_employee_id ON employee_documents(employee_id)"))

        if "users" in tables:
            user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
            if "employee_id" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN employee_id INTEGER"))

        if "departments" in tables:
            dept_columns = {column["name"] for column in inspect(engine).get_columns("departments")}
            if "branch_id" not in dept_columns:
                connection.execute(text("ALTER TABLE departments ADD COLUMN branch_id INTEGER"))
            # Update unique constraint from name to name + branch_id
            try:
                connection.execute(text("ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_name_key"))
            except:
                pass

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
                "zkteco_enabled": "ALTER TABLE company_settings ADD COLUMN zkteco_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                "zkteco_ip": "ALTER TABLE company_settings ADD COLUMN zkteco_ip VARCHAR(50) NOT NULL DEFAULT '192.168.1.201'",
                "zkteco_port": "ALTER TABLE company_settings ADD COLUMN zkteco_port INTEGER NOT NULL DEFAULT 4370",
                "zkteco_password": "ALTER TABLE company_settings ADD COLUMN zkteco_password VARCHAR(100) NOT NULL DEFAULT ''",
                "zkteco_auto_sync_enabled": "ALTER TABLE company_settings ADD COLUMN zkteco_auto_sync_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                "zkteco_auto_sync_interval_minutes": "ALTER TABLE company_settings ADD COLUMN zkteco_auto_sync_interval_minutes INTEGER NOT NULL DEFAULT 30",
                "branch_id": "ALTER TABLE company_settings ADD COLUMN branch_id INTEGER",
            }
            for column_name, statement in statements.items():
                if column_name not in setting_columns:
                    try:
                        connection.execute(text(statement))
                    except:
                        pass
            # Add unique constraint for branch_id if not exists
            try:
                connection.execute(text("ALTER TABLE company_settings ADD CONSTRAINT uq_company_settings_branch_id UNIQUE (branch_id)"))
            except:
                pass

        if "employees" in tables:
            employee_columns = {column["name"] for column in inspect(engine).get_columns("employees")}
            statements = {
                "branch_id": "ALTER TABLE employees ADD COLUMN branch_id INTEGER",
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
                    try:
                        connection.execute(text(statement))
                    except:
                        pass


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
