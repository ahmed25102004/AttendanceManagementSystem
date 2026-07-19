from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.shift import Shift
from app.schemas.shift import ShiftCreate, ShiftUpdate


class ShiftService:
    def create(self, db: Session, payload: ShiftCreate, branch_id: int | None) -> Shift:
        if payload.start_time >= payload.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="وقت البداية يجب أن يكون قبل وقت النهاية.",
            )
        
        # Check if shift with same name exists in branch
        existing = db.query(Shift).filter(
            Shift.name == payload.name,
            Shift.branch_id == branch_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="الوردية بهذا الاسم موجودة بالفعل في هذا الفرع.",
            )
        
        data = payload.model_dump()
        if branch_id:
            data["branch_id"] = branch_id
        shift = Shift(**data)
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    def list(self, db: Session, branch_id: int | None) -> list[Shift]:
        query = db.query(Shift)
        if branch_id:
            query = query.filter(Shift.branch_id == branch_id)
        return query.order_by(Shift.id.desc()).all()

    def get(self, db: Session, shift_id: int, branch_id: int | None = None) -> Shift:
        query = db.query(Shift).filter(Shift.id == shift_id)
        if branch_id:
            query = query.filter(Shift.branch_id == branch_id)
        shift = query.first()
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الوردية غير موجودة.",
            )
        return shift

    def update(self, db: Session, shift_id: int, payload: ShiftUpdate, branch_id: int | None) -> Shift:
        shift = self.get(db, shift_id, branch_id)
        
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
        
        # Check if name is being changed and if it conflicts
        if payload.name:
            existing = db.query(Shift).filter(
                Shift.name == payload.name,
                Shift.branch_id == (branch_id or shift.branch_id),
                Shift.id != shift_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="الوردية بهذا الاسم موجودة بالفعل في هذا الفرع.",
                )

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(shift, key, value)
        
        db.commit()
        db.refresh(shift)
        return shift

    def delete(self, db: Session, shift_id: int, branch_id: int | None) -> None:
        shift = self.get(db, shift_id, branch_id)
        db.delete(shift)
        db.commit()
