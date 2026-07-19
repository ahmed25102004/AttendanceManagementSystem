from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_required_branch_id
from app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftResponse
from app.services.shift_service import ShiftService


router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])
shift_service = ShiftService()


@router.get("", response_model=list[ShiftResponse])
def list_shifts(
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    all: bool = Query(False, description="Return all shifts regardless of current branch selection")
):
    return shift_service.list(db, None if all else branch_id)


@router.post("", response_model=ShiftResponse, status_code=201)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id)
):
    return shift_service.create(db, payload, branch_id)


@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    all: bool = Query(False, description="Return shift regardless of branch")
):
    return shift_service.get(db, shift_id, None if all else branch_id)


@router.put("/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id)
):
    return shift_service.update(db, shift_id, payload, branch_id)


@router.delete("/{shift_id}", status_code=204)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id)
):
    shift_service.delete(db, shift_id, branch_id)
