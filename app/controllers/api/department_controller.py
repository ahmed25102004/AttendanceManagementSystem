from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db, get_current_branch_id
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentResponse


router = APIRouter(dependencies=[Depends(get_admin_user)])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    query = db.query(Department)
    if branch_id:
        query = query.filter(Department.branch_id == branch_id)
    return query.order_by(Department.name.asc()).all()


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    # Check if a department with the same name exists in the same branch
    query = db.query(Department).filter(Department.name == payload.name)
    if branch_id:
        query = query.filter(Department.branch_id == branch_id)
    existing = query.first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل في هذا الفرع.")
    
    # Create payload without branch_id first, then add it
    data = payload.model_dump()
    if branch_id:
        data["branch_id"] = branch_id
    department = Department(**data)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, payload: DepartmentCreate, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="القسم غير موجود.")
    
    # Check if a department with the same name exists in the same branch (but not the same department)
    query = db.query(Department).filter(Department.name == payload.name, Department.id != department_id)
    if branch_id:
        query = query.filter(Department.branch_id == branch_id)
    existing = query.first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل في هذا الفرع.")
    
    # Update fields
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(department, key, value)
    if branch_id:
        department.branch_id = branch_id
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
