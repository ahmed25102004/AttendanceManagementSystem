from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftResponse
from app.services.shift_service import ShiftService


router = APIRouter(dependencies=[Depends(get_admin_user)])
shift_service = ShiftService()


@router.get("", response_model=list[ShiftResponse])
def list_shifts(db: Session = Depends(get_db)):
    return shift_service.list(db)


@router.post("", response_model=ShiftResponse, status_code=201)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db)):
    return shift_service.create(db, payload)


@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    return shift_service.get(db, shift_id)


@router.put("/{shift_id}", response_model=ShiftResponse)
def update_shift(shift_id: int, payload: ShiftUpdate, db: Session = Depends(get_db)):
    return shift_service.update(db, shift_id, payload)


@router.delete("/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    return shift_service.delete(db, shift_id)
