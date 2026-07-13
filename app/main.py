import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.controllers.api import (
    attendance_controller,
    attendance_log_controller,
    auth_controller,
    backup_controller,
    branch_controller,
    dashboard_controller,
    department_controller,
    device_controller,
    employee_controller,
    employee_document_controller,
    iclock_controller,
    leave_controller,
    monitoring_controller,
    notification_controller,
    report_controller,
    setting_controller,
    shift_controller,
    task_controller,
)
from app.controllers.web import page_controller
from app.core.bootstrap import bootstrap_defaults
from app.core.config import get_settings
from app.core.database import Base, engine
from app.models import (
    AttendanceRecord,
    Branch,
    CompanySetting,
    Department,
    Employee,
    EmployeeDocument,
    Leave,
    Notification,
    Shift,
    Task,
    User,
)


settings = get_settings()
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_defaults()
    
    # Start scheduler and set up initial job
    scheduler.start()
    from app.controllers.api.setting_controller import update_scheduler_job
    update_scheduler_job()
    
    yield
    
    # Shutdown scheduler
    scheduler.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/views/static"), name="static")

app.include_router(page_controller.router)
app.include_router(auth_controller.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard_controller.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(department_controller.router, prefix="/api/departments", tags=["Departments"])
app.include_router(device_controller.router, prefix="/api/devices", tags=["Devices"])
app.include_router(employee_controller.router, prefix="/api/employees", tags=["Employees"])
app.include_router(employee_document_controller.router, prefix="/api/employee-documents", tags=["Employee Documents"])
app.include_router(leave_controller.router, prefix="/api/leaves", tags=["Leaves"])
app.include_router(monitoring_controller.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(notification_controller.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(shift_controller.router, prefix="/api/shifts", tags=["Shifts"])
app.include_router(task_controller.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(attendance_controller.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(attendance_log_controller.router, prefix="/api/attendance-logs", tags=["Attendance Logs"])
app.include_router(report_controller.router, prefix="/api/reports", tags=["Reports"])
app.include_router(setting_controller.router, prefix="/api/settings", tags=["Settings"])
app.include_router(backup_controller.router, prefix="/api/backups", tags=["Backups"])
app.include_router(branch_controller.router, prefix="/api/branches", tags=["Branches"])
app.include_router(iclock_controller.router, prefix="/iclock", tags=["iClock ADMS"])
app.include_router(iclock_controller.router, prefix="/attendance", tags=["Device Attendance"])
