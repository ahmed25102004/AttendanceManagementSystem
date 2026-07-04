from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.shift import Shift
from app.schemas.shift import ShiftCreate, ShiftUpdate


class ShiftService:
    def create(self, db: Session, payload: ShiftCreate) -> Shift:
        if payload.start_time >= payload.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="وقت البداية يجب أن يكون قبل وقت النهاية.",
            )
        
        shift = Shift(**payload.model_dump())
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    def list(self, db: Session) -> list[Shift]:
        return db.query(Shift).order_by(Shift.id.desc()).all()

    def get(self, db: Session, shift_id: int) -> Shift:
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الوردية غير موجودة.",
            )
        return shift

    def update(self, db: Session, shift_id: int, payload: ShiftUpdate) -> Shift:
        shift = self.get(db, shift_id)
        
        if (payload.start_time is not None and payload.end_time is not None):
            if payload.start_time >= payload.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="وقت البداية يجب أن يكون قبل وقت النهاية.",
                )
        elif payload.start_time is not None:
            if payload.start_time >= shift.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="وقت البداية يجب أن يكون قبل وقت النهاية.",
                )
        elif payload.end_time is not None:
            if shift.start_time >= payload.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="وقت البداية يجب أن يكون قبل وقت النهاية.",
                )

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(shift, key, value)

        db.commit()
        db.refresh(shift)
        return shift

    def delete(self, db: Session, shift_id: int) -> None:
        shift = self.get(db, shift_id)
        db.delete(shift)
        db.commit()
