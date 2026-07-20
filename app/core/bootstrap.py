from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.security import security_manager
from app.models.branch import Branch
from app.models.company_setting import CompanySetting
from app.models.department import Department
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
            connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
            connection.execute(
                text(
                    "ALTER TABLE departments "
                    "ADD COLUMN IF NOT EXISTS attendance_policy VARCHAR(50) NOT NULL DEFAULT 'default'"
                )
            )
            connection.execute(
                text(
                    "UPDATE departments SET attendance_policy = 'default' "
                    "WHERE attendance_policy IS NULL OR attendance_policy = ''"
                )
            )

            # Update unique constraint from name to name + branch_id
            try:
                connection.execute(text("ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_name_key"))
            except:
                pass
            try:
                department_constraints = {
                    constraint["name"]
                    for constraint in inspect(connection).get_unique_constraints("departments")
                    if constraint.get("name")
                }
                if "uq_departments_branch_id_name" not in department_constraints:
                    connection.execute(
                        text(
                            "ALTER TABLE departments "
                            "ADD CONSTRAINT uq_departments_branch_id_name UNIQUE (branch_id, name)"
                        )
                    )
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
                "employment_type": "ALTER TABLE employees ADD COLUMN employment_type VARCHAR(50) NOT NULL DEFAULT 'full_time'",
                "shift_id": "ALTER TABLE employees ADD COLUMN shift_id INTEGER",
                "weekly_rest_day": "ALTER TABLE employees ADD COLUMN weekly_rest_day VARCHAR(20)",
            }
            for column_name, statement in statements.items():
                if column_name not in employee_columns:
                    try:
                        connection.execute(text(statement))
                    except:
                        pass

        # Create employee_shift_schedules table if not exists
        if "employee_shift_schedules" not in tables:
            connection.execute(text("""
                CREATE TABLE employee_shift_schedules (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    day_of_week VARCHAR(20) NOT NULL,
                    shift_type VARCHAR(50) NOT NULL,
                    shift_id INTEGER REFERENCES shifts(id)
                )
            """))
            connection.execute(text("CREATE INDEX idx_employee_shift_schedules_employee_id ON employee_shift_schedules(employee_id)"))

        if "attendance_records" in tables:
            attendance_columns = {column["name"] for column in inspect(engine).get_columns("attendance_records")}
            attendance_statements = {
                "late_minutes": "ALTER TABLE attendance_records ADD COLUMN late_minutes INTEGER NOT NULL DEFAULT 0",
                "is_rest_day": "ALTER TABLE attendance_records ADD COLUMN is_rest_day BOOLEAN NOT NULL DEFAULT FALSE",
                "worked_on_rest_day": "ALTER TABLE attendance_records ADD COLUMN worked_on_rest_day BOOLEAN NOT NULL DEFAULT FALSE",
            }
            for col_name, col_stmt in attendance_statements.items():
                if col_name not in attendance_columns:
                    try:
                        connection.execute(text(col_stmt))
                    except:
                        pass


def ensure_departments_schema_compatibility() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "departments" not in inspector.get_table_names():
            return

        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
        connection.execute(
            text(
                "ALTER TABLE departments "
                "ADD COLUMN IF NOT EXISTS attendance_policy VARCHAR(50) NOT NULL DEFAULT 'default'"
            )
        )
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        connection.execute(
            text(
                "UPDATE departments SET attendance_policy = 'default' "
                "WHERE attendance_policy IS NULL OR attendance_policy = ''"
            )
        )
        
        # Add old fields for doctors department shift settings (backward compatibility)
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS half_shift_start_time TIME DEFAULT '08:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS half_shift_end_time TIME DEFAULT '15:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS half_shift_hours INTEGER DEFAULT 7"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS full_shift_start_time TIME DEFAULT '08:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS full_shift_end_time TIME DEFAULT '22:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS full_shift_hours INTEGER DEFAULT 14"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS overtime_start_time TIME DEFAULT '15:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS grace_period_minutes INTEGER DEFAULT 30"))
        
        # Add NEW fields for unified department shift settings
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS shift_start_time TIME DEFAULT '08:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS shift_end_time TIME DEFAULT '15:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS shift_hours INTEGER DEFAULT 7"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS late_start_time TIME DEFAULT '08:30:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS attendance_end_time TIME DEFAULT '11:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS overtime_enabled BOOLEAN NOT NULL DEFAULT TRUE"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS overtime_start_time TIME DEFAULT '15:00:00'"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS evening_shift_start_time TIME"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS evening_shift_end_time TIME"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS evening_shift_hours INTEGER"))
        connection.execute(text("ALTER TABLE departments ADD COLUMN IF NOT EXISTS evening_shift_late_start_time TIME"))


def ensure_employees_schema_compatibility() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "employees" not in inspector.get_table_names():
            return

        compatibility_statements = [
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS branch_id INTEGER",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS face_images JSON",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS face_descriptor JSON",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS face_registered_at TIMESTAMP",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS face_verification_enabled BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS employment_type VARCHAR(50) NOT NULL DEFAULT 'full_time'",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS shift_id INTEGER",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS weekly_rest_day VARCHAR(20)",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS annual_leave_balance INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE employees ADD COLUMN IF NOT EXISTS sick_leave_balance INTEGER NOT NULL DEFAULT 0",
        ]
        for statement in compatibility_statements:
            connection.execute(text(statement))


def ensure_shifts_schema_compatibility() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "shifts" not in inspector.get_table_names():
            return

        compatibility_statements = [
            "ALTER TABLE shifts ADD COLUMN IF NOT EXISTS branch_id INTEGER",
        ]
        for statement in compatibility_statements:
            connection.execute(text(statement))
        
        # Drop old unique constraint on name
        try:
            connection.execute(text("ALTER TABLE shifts DROP CONSTRAINT IF EXISTS shifts_name_key"))
        except:
            pass
        
        # Add new unique constraint on (branch_id, name)
        try:
            connection.execute(text("ALTER TABLE shifts ADD CONSTRAINT uq_branch_shift_name UNIQUE (branch_id, name)"))
        except:
            pass


def ensure_attendance_records_schema_compatibility() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "attendance_records" not in inspector.get_table_names():
            return

        compatibility_statements = [
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS late_minutes INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS is_rest_day BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS worked_on_rest_day BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS shift_category VARCHAR(30)",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS shift_units DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS overtime_hours REAL NOT NULL DEFAULT 0.0",
            "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS shift_deficit_hours REAL NOT NULL DEFAULT 0.0",
        ]
        for statement in compatibility_statements:
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
    ensure_departments_schema_compatibility()
    ensure_employees_schema_compatibility()
    ensure_shifts_schema_compatibility()
    ensure_attendance_records_schema_compatibility()
    db: Session = SessionLocal()
    try:
        company_settings = db.query(CompanySetting).first()
        if not company_settings:
            company_settings = CompanySetting(company_name=settings.company_name)
            db.add(company_settings)
        
        # Create default branches
        branch1 = db.query(Branch).filter(Branch.name == "فرع المسله").first()
        if not branch1:
            branch1 = Branch(name="فرع المسله")
            db.add(branch1)
        branch2 = db.query(Branch).filter(Branch.name == "فرع بني سويف").first()
        if not branch2:
            branch2 = Branch(name="فرع بني سويف")
            db.add(branch2)
        db.flush()
        
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
        
        from app.models.shift import Shift
        from datetime import time
        
        # For each branch, create default departments and shifts
        branches = db.query(Branch).all()
        for branch in branches:
            # Create Leather Department for this branch if it doesn't exist
            leather_dept = db.query(Department).filter(
                Department.name == "قسم الجلدية",
                Department.branch_id == branch.id
            ).first()
            if not leather_dept:
                leather_dept = Department(
                    name="قسم الجلدية",
                    description="قسم الجلدية - نظام ساعات عمل فقط بدون شيفتات أو تأخير",
                    attendance_policy="leather_department",
                    branch_id=branch.id
                )
                db.add(leather_dept)
                
            # Create Reception Department for this branch if it doesn't exist
            reception_dept = db.query(Department).filter(
                Department.name == "قسم الريسبشن",
                Department.branch_id == branch.id
            ).first()
            if not reception_dept:
                from datetime import time
                reception_dept = Department(
                    name="قسم الريسبشن",
                    description="قسم الريسبشن - نظام شيفتات وإجازة أسبوعية",
                    attendance_policy="reception_department",
                    branch_id=branch.id,
                    # Unified shift settings
                    shift_start_time=time(8, 0),
                    shift_end_time=time(16, 0),
                    shift_hours=8,
                    late_start_time=time(8, 15),
                    attendance_end_time=time(10, 0),
                    overtime_enabled=True,
                    overtime_start_time=time(16, 0),
                    # Default evening shift settings
                    evening_shift_start_time=time(16, 0),
                    evening_shift_end_time=time(23, 59),
                    evening_shift_hours=8,
                    evening_shift_late_start_time=time(16, 15),
                    # Old fields (backward compatibility)
                    half_shift_start_time=time(8, 0),
                    half_shift_end_time=time(15, 0),
                    half_shift_hours=7,
                    full_shift_start_time=time(8, 0),
                    full_shift_end_time=time(22, 0),
                    full_shift_hours=14,
                    grace_period_minutes=15
                )
                db.add(reception_dept)
                
            # Create Workers Department for this branch if it doesn't exist
            workers_dept = db.query(Department).filter(
                Department.name == "قسم العمال",
                Department.branch_id == branch.id
            ).first()
            if not workers_dept:
                from datetime import time
                workers_dept = Department(
                    name="قسم العمال",
                    description="قسم العمال - نظام شيفتات وإجازة أسبوعية",
                    attendance_policy="workers_department",
                    branch_id=branch.id,
                    # Unified shift settings
                    shift_start_time=time(7, 0),
                    shift_end_time=time(15, 0),
                    shift_hours=8,
                    late_start_time=time(7, 15),
                    attendance_end_time=time(9, 0),
                    overtime_enabled=True,
                    overtime_start_time=time(15, 0),
                    # Default evening shift settings
                    evening_shift_start_time=time(15, 0),
                    evening_shift_end_time=time(23, 0),
                    evening_shift_hours=8,
                    evening_shift_late_start_time=time(15, 15),
                    # Old fields (backward compatibility)
                    half_shift_start_time=time(8, 0),
                    half_shift_end_time=time(15, 0),
                    half_shift_hours=7,
                    full_shift_start_time=time(8, 0),
                    full_shift_end_time=time(22, 0),
                    full_shift_hours=14,
                    grace_period_minutes=15
                )
                db.add(workers_dept)
                
            # Create Doctors Department for this branch if it doesn't exist
            from datetime import time
            doctors_dept = db.query(Department).filter(
                Department.name == "الدكاتره",
                Department.branch_id == branch.id
            ).first()
            if not doctors_dept:
                doctors_dept = Department(
                    name="الدكاتره",
                    description="قسم الدكاتره - نظام شفت كامل ونصف شفت مع اوفر تايم",
                    attendance_policy="doctors_department",
                    branch_id=branch.id,
                    # New fields
                    shift_start_time=time(8, 0),
                    shift_end_time=time(15, 0),
                    shift_hours=7,
                    late_start_time=time(8, 30),
                    attendance_end_time=time(11, 0),
                    overtime_enabled=True,
                    overtime_start_time=time(15, 0),
                    # Old fields (backward compatibility)
                    half_shift_start_time=time(8, 0),
                    half_shift_end_time=time(15, 0),
                    half_shift_hours=7,
                    full_shift_start_time=time(8, 0),
                    full_shift_end_time=time(22, 0),
                    full_shift_hours=14,
                    grace_period_minutes=30
                )
                db.add(doctors_dept)
                
            # Create default shifts for this branch if they don't exist
            morning_shift = db.query(Shift).filter(
                Shift.name == "صباحي",
                Shift.branch_id == branch.id
            ).first()
            if not morning_shift:
                morning_shift = Shift(
                    name="صباحي",
                    start_time=time(7, 30),
                    end_time=time(14, 30),
                    grace_period_minutes=15,
                    branch_id=branch.id
                )
                db.add(morning_shift)
                
            evening_shift = db.query(Shift).filter(
                Shift.name == "مسائي",
                Shift.branch_id == branch.id
            ).first()
            if not evening_shift:
                evening_shift = Shift(
                    name="مسائي",
                    start_time=time(14, 0),
                    end_time=time(21, 30),
                    grace_period_minutes=15,
                    branch_id=branch.id
                )
                db.add(evening_shift)
                
        employees = db.query(Employee).all()
        for employee in employees:
            _sync_employee_user(db, employee)

        db.commit()
    finally:
        db.close()
