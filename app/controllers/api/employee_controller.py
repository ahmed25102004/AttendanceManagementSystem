from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db, get_current_branch_id
from app.schemas.employee import (
    EmployeeCreate, 
    EmployeeResponse, 
    EmployeeUpdate, 
    EmployeeProfileResponse,
    AttendanceLogEntry,
    EmployeeStatsResponse
)
from app.services.employee_service import EmployeeService


router = APIRouter(dependencies=[Depends(get_admin_user)])
employee_service = EmployeeService()


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    search: str | None = Query(None),
    department_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    employment_type: str | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return all employees regardless of current branch selection")
):
    return employee_service.list(db, search, None if all else branch_id, department_id, is_active, employment_type)


@router.get("/{employee_id}", response_model=EmployeeProfileResponse)
def get_employee_profile(
    employee_id: int, 
    db: Session = Depends(get_db), 
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return employee regardless of branch")
):
    return employee_service.get_profile(db, employee_id, None if all else branch_id)


@router.get("/{employee_id}/attendance-logs", response_model=list[AttendanceLogEntry])
def get_employee_attendance_logs(
    employee_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return logs regardless of branch")
):
    return employee_service.get_attendance_logs(db, employee_id, start_date, end_date, None if all else branch_id)


@router.get("/{employee_id}/stats", response_model=EmployeeStatsResponse)
def get_employee_stats(
    employee_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return stats regardless of branch")
):
    return employee_service.get_stats(db, employee_id, start_date, end_date, None if all else branch_id)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return employee_service.create(db, payload, branch_id)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return employee_service.update(db, employee_id, payload, branch_id)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    employee_service.delete(db, employee_id, branch_id)
