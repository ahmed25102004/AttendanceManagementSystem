from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_required_branch_id, resolve_branch_scope
from app.schemas.employee import (
    EmployeeCreate, 
    EmployeeResponse, 
    EmployeeUpdate, 
    EmployeeProfileResponse,
    AttendanceLogEntry,
    EmployeeShiftScheduleResponse,
    EmployeeShiftScheduleUpdate,
    EmployeeStatsResponse
)
from app.services.employee_service import EmployeeService


router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])
employee_service = EmployeeService()


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    search: str | None = Query(None),
    department_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    employment_type: str | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Return all employees regardless of current branch selection")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.list(db, search, scoped_branch_id, department_id, is_active, employment_type)


@router.get("/{employee_id}", response_model=EmployeeProfileResponse)
def get_employee_profile(
    employee_id: int, 
    db: Session = Depends(get_db), 
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Return employee regardless of branch")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.get_profile(db, employee_id, scoped_branch_id)


@router.get("/{employee_id}/attendance-logs", response_model=list[AttendanceLogEntry])
def get_employee_attendance_logs(
    employee_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Return logs regardless of branch")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.get_attendance_logs(db, employee_id, start_date, end_date, scoped_branch_id)


@router.get("/{employee_id}/stats", response_model=EmployeeStatsResponse)
def get_employee_stats(
    employee_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Return stats regardless of branch")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.get_stats(db, employee_id, start_date, end_date, scoped_branch_id)


@router.get("/{employee_id}/shift-schedule", response_model=EmployeeShiftScheduleResponse)
def get_employee_shift_schedule(
    employee_id: int,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Return employee schedule regardless of branch")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.get_shift_schedule(db, employee_id, scoped_branch_id)


@router.put("/{employee_id}/shift-schedule", response_model=EmployeeShiftScheduleResponse)
def update_employee_shift_schedule(
    employee_id: int,
    payload: EmployeeShiftScheduleUpdate,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    current_user=Depends(get_branch_manager_or_admin),
    all: bool = Query(False, description="Update employee schedule regardless of branch")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    return employee_service.update_shift_schedule(db, employee_id, payload, scoped_branch_id)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    return employee_service.create(db, payload, branch_id)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    return employee_service.update(db, employee_id, payload, branch_id)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    employee_service.delete(db, employee_id, branch_id)
