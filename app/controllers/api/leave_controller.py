from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_employee_user, get_db
from app.schemas.leave import LeaveCreate, LeaveUpdate, LeaveResponse
from app.services.leave_service import LeaveService


router = APIRouter()
leave_service = LeaveService()


@router.get("", response_model=list[LeaveResponse], dependencies=[Depends(get_admin_user)])
def list_leaves(employee_id: int | None = Query(None), db: Session = Depends(get_db)):
    return leave_service.list(db, employee_id)


@router.post("", response_model=LeaveResponse, status_code=201)
def create_leave(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_employee_user)
):
    return leave_service.create(db, payload)


@router.get("/my", response_model=list[LeaveResponse], dependencies=[Depends(get_employee_user)])
def get_my_leaves(db: Session = Depends(get_db), current_user: dict = Depends(get_employee_user)):
    return leave_service.list(db, current_user.employee_id)


@router.get("/{leave_id}", response_model=LeaveResponse)
def get_leave(leave_id: int, db: Session = Depends(get_db), _: dict = Depends(get_admin_user)):
    return leave_service.get(db, leave_id)


@router.put("/{leave_id}", response_model=LeaveResponse, dependencies=[Depends(get_admin_user)])
def update_leave(leave_id: int, payload: LeaveUpdate, db: Session = Depends(get_db)):
    return leave_service.update(db, leave_id, payload)


@router.delete("/{leave_id}", status_code=204, dependencies=[Depends(get_admin_user)])
def delete_leave(leave_id: int, db: Session = Depends(get_db)):
    return leave_service.delete(db, leave_id)
