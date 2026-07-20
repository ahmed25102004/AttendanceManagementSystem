from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import decode_token_safely
from app.core.dependencies import get_db
from app.models.department import Department
from app.models.user import User


router = APIRouter()
templates = Jinja2Templates(directory="app/views/templates")


def _get_request_user(request: Request, db: Session) -> User | None:
    raw_token = request.cookies.get("attendance_token")
    if not raw_token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            raw_token = authorization[7:]

    if not raw_token:
        return None

    username = decode_token_safely(raw_token)
    if not username:
        return None

    return (
        db.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .first()
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "page": "login"})
    return templates.TemplateResponse("branch_selection.html", {"request": request, "page": "home"})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "page": "login"})


@router.get("/employees", response_class=HTMLResponse)
def employees(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("employees.html", {"request": request, "page": "employees"})


@router.get("/attendance", response_class=HTMLResponse)
def attendance(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("attendance.html", {"request": request, "page": "attendance"})


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("reports.html", {"request": request, "page": "reports"})


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request, "page": "settings"})


@router.get("/branches", response_class=HTMLResponse)
def branches(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("branches.html", {"request": request, "page": "branches"})


@router.get("/branches/{branch_id}", response_class=HTMLResponse)
def branch_dashboard(branch_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("branch_dashboard.html", {"request": request, "page": "branches", "branch_id": branch_id})


@router.get("/departments", response_class=HTMLResponse)
def departments(request: Request, db: Session = Depends(get_db)):
    # Redirect to branch dashboard since we don't have an all-departments page
    branch_id = request.query_params.get("branch_id")
    if not branch_id:
        # If no branch, go back to home
        return RedirectResponse("/", status_code=302)
    return RedirectResponse(f"/branches/{branch_id}", status_code=302)


@router.get("/departments/{department_id}", response_class=HTMLResponse)
def department_page(department_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("department_page.html", {"request": request, "page": "departments", "department_id": department_id})


@router.get("/shifts", response_class=HTMLResponse)
def shifts(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("shifts.html", {"request": request, "page": "shifts"})


@router.get("/backups", response_class=HTMLResponse)
def backups(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("backups.html", {"request": request, "page": "backups"})


@router.get("/devices", response_class=HTMLResponse)
def devices(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("devices.html", {"request": request, "page": "devices"})


@router.get("/multi-branch-dashboard", response_class=HTMLResponse)
def multi_branch_dashboard(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("multi_branch_dashboard.html", {"request": request, "page": "multi-branch-dashboard"})





@router.get("/employees/{employee_id}", response_class=HTMLResponse)
def employee_profile(employee_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("employee_profile.html", {"request": request, "page": "employees", "employee_id": employee_id})


@router.get("/monitoring", response_class=HTMLResponse)
def monitoring(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role not in ["admin", "branch_manager"]:
        return RedirectResponse("/my-attendance", status_code=302)
    return templates.TemplateResponse("monitoring.html", {"request": request, "page": "monitoring"})


@router.get("/my-attendance", response_class=HTMLResponse)
def my_attendance(request: Request, db: Session = Depends(get_db)):
    user = _get_request_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role == "admin":
        return RedirectResponse("/employees", status_code=302)
    return templates.TemplateResponse("my_attendance.html", {"request": request, "page": "my-attendance"})
