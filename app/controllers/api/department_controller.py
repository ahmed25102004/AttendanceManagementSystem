from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentResponse


router = APIRouter(dependencies=[Depends(get_admin_user)])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).order_by(Department.name.asc()).all()


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(Department).filter(Department.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل.")
    department = Department(**payload.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, payload: DepartmentCreate, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="القسم غير موجود.")
    existing = db.query(Department).filter(Department.name == payload.name, Department.id != department_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل.")
    for key, value in payload.model_dump().items():
        setattr(department, key, value)
    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="القسم غير موجود.")
    # Set department_id to null for all employees in this department
    db.query(Employee).filter(Employee.department_id == department_id).update({"department_id": None})
    db.delete(department)
    db.commit()
