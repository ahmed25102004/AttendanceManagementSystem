# Employee Attendance Management System

A complete single-company employee attendance management system built with FastAPI, PostgreSQL, JWT authentication, Bootstrap, HTML, CSS, and vanilla JavaScript.

## Features

- Secure admin login with JWT authentication
- Dashboard with attendance KPIs
- Employee and department management
- Check-in / check-out attendance workflow
- Daily and monthly reports
- Excel and PDF export
- Company settings for working hours, weekends, and late threshold
- MVC-style project structure with OOP service layer
- Attendance verification abstraction ready for future face recognition integration

## Project Structure

```text
app/
  controllers/
    api/
    web/
  core/
  models/
  schemas/
  services/
  views/
    static/
    templates/
scripts/
```

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create PostgreSQL database:

   ```sql
   CREATE DATABASE attendance_db;
   ```

4. Copy `.env.example` to `.env` and update credentials.
5. Start the application:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open `http://127.0.0.1:8000`

## Default Admin Account

On first startup, the system creates the admin account configured in `.env`.

Default example credentials:

- Username: `admin`
- Password: `Admin@123`

## Notes

- The system is designed for a single company, not SaaS.
- The attendance module includes a verification provider abstraction so face recognition can be added later without redesigning the attendance records model.
