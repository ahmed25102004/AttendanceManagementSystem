from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db, get_employee_user, get_current_branch_id
from app.schemas.attendance import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceResponse,
    FaceAttendanceRequest,
    FacePortalStatusResponse,
    FaceRegistrationRequest,
    FaceRegistrationResponse,
    FaceScanResponse,
    SelfAttendanceRequest,
)
from app.services.attendance_service import AttendanceService


router = APIRouter()
attendance_service = AttendanceService()


@router.get("", response_model=list[AttendanceResponse])
def list_attendance(
    attendance_date: date | None = Query(default=None),
    _: object = Depends(get_admin_user),
    db: Session = Depends(get_db),
    branch_id: int | None = Depends(get_current_branch_id),
    all: bool = Query(False, description="Return all attendance records regardless of current branch selection")
):
    return attendance_service.list_records(db, attendance_date, None if all else branch_id)


@router.post("/check-in", response_model=AttendanceResponse)
def check_in(payload: AttendanceCheckIn, _: object = Depends(get_admin_user), db: Session = Depends(get_db)):
    return attendance_service.check_in(db, payload)


@router.post("/check-out", response_model=AttendanceResponse)
def check_out(payload: AttendanceCheckOut, _: object = Depends(get_admin_user), db: Session = Depends(get_db)):
    return attendance_service.check_out(db, payload)


@router.get("/self/today", response_model=AttendanceResponse | None)
def self_today(
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.get_today_record_for_user(db, current_user)


@router.get("/self/face/status", response_model=FacePortalStatusResponse)
def self_face_status(
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.get_face_portal_status(db, current_user)


@router.post("/self/face/register", response_model=FaceRegistrationResponse)
def self_face_register(
    payload: FaceRegistrationRequest,
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.register_face(db, current_user, payload)


@router.post("/self/face/scan", response_model=FaceScanResponse)
def self_face_scan(
    payload: FaceAttendanceRequest,
    request: Request,
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.process_face_scan(db, current_user, request, payload)


@router.post("/self/check-in", response_model=AttendanceResponse)
def self_check_in(
    payload: SelfAttendanceRequest,
    request: Request,
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.self_check_in(db, current_user, request, payload)


@router.post("/self/check-out", response_model=AttendanceResponse)
def self_check_out(
    payload: SelfAttendanceRequest,
    request: Request,
    current_user=Depends(get_employee_user),
    db: Session = Depends(get_db),
):
    return attendance_service.self_check_out(db, current_user, request, payload)
