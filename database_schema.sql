CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    employee_code VARCHAR(30) NOT NULL UNIQUE,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(30),
    address TEXT,
    job_title VARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    department_id INTEGER REFERENCES departments(id)
);

CREATE TABLE company_settings (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    work_start_time TIME NOT NULL DEFAULT '09:00:00',
    work_end_time TIME NOT NULL DEFAULT '17:00:00',
    weekend_days VARCHAR(50) NOT NULL DEFAULT 'Saturday,Sunday',
    late_grace_minutes INTEGER NOT NULL DEFAULT 15
);

CREATE TABLE attendance_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    attendance_date DATE NOT NULL,
    check_in_time TIMESTAMP NULL,
    check_out_time TIMESTAMP NULL,
    working_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'present',
    source_type VARCHAR(30) NOT NULL DEFAULT 'manual',
    verification_data JSONB NULL
);

CREATE INDEX idx_employees_code ON employees(employee_code);
CREATE INDEX idx_employees_email ON employees(email);
CREATE INDEX idx_attendance_employee_date ON attendance_records(employee_id, attendance_date);
