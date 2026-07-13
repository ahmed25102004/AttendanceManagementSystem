from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.user import User


router = APIRouter()
templates = Jinja2Templates(directory="app/views/templates")


def _get_request_user(db: Session) -> User | None:
    # Always return admin, no auth checks
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        return user
    # If admin doesn't exist, return first active user
    user = db.query(User).filter(User.is_active.is_(True)).first()
    if user:
        return user
    return None


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if user:
        return RedirectResponse("/dashboard" if user.role == "admin" else "/my-attendance", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "page": "login"})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "dashboard"})


@router.get("/employees", response_class=HTMLResponse)
def employees(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("employees.html", {"request": request, "page": "employees"})


@router.get("/attendance", response_class=HTMLResponse)
def attendance(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("attendance.html", {"request": request, "page": "attendance"})


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("reports.html", {"request": request, "page": "reports"})


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request, "page": "settings"})


@router.get("/branches", response_class=HTMLResponse)
def branches(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("branches.html", {"request": request, "page": "branches"})


@router.get("/branches/{branch_id}", response_class=HTMLResponse)
def branch_dashboard(branch_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("branch_dashboard.html", {"request": request, "page": "branches", "branch_id": branch_id})


@router.get("/departments", response_class=HTMLResponse)
def departments(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("departments.html", {"request": request, "page": "departments"})


@router.get("/leaves", response_class=HTMLResponse)
def leaves(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("leaves.html", {"request": request, "page": "leaves"})


@router.get("/tasks", response_class=HTMLResponse)
def tasks(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("tasks.html", {"request": request, "page": "tasks"})


@router.get("/shifts", response_class=HTMLResponse)
def shifts(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("shifts.html", {"request": request, "page": "shifts"})


@router.get("/backups", response_class=HTMLResponse)
def backups(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("backups.html", {"request": request, "page": "backups"})


@router.get("/devices", response_class=HTMLResponse)
def devices(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("devices.html", {"request": request, "page": "devices"})


@router.get("/monitoring", response_class=HTMLResponse)
def monitoring(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("monitoring.html", {"request": request, "page": "monitoring"})


@router.get("/my-attendance", response_class=HTMLResponse)
def my_attendance(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(db)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user.role == "admin":
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("my_attendance.html", {"request": request, "page": "my-attendance"})
