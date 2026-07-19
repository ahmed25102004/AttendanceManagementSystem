from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_current_branch_id
from app.schemas.attendance_log import AttendanceLogResponse
from app.services.attendance_log_service import AttendanceLogService


router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])
attendance_log_service = AttendanceLogService()


@router.get("", response_model=list[AttendanceLogResponse])
def list_attendance_logs(
    device_id: int | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    employee_code: str | None = Query(None),
    attendance_type: str | None = Query(None),
    verify_type: str | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return all attendance logs regardless of current branch selection")
):
    return attendance_log_service.list(db, None if all else branch_id, device_id, start_date, end_date, employee_code, attendance_type, verify_type)
