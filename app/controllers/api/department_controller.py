from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_required_branch_id
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.services.department_service import DepartmentService

department_service = DepartmentService()


router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    return department_service.list(db, branch_id)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(department_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    return department_service.get(db, department_id, branch_id)


@router.get("/{department_id}/stats")
def get_department_stats(department_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    return department_service.get_stats(db, department_id, branch_id)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    # Check if a department with the same name exists in the same branch
    query = db.query(Department).filter(Department.name == payload.name, Department.branch_id == branch_id)
    existing = query.first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل في هذا الفرع.")
    
    # Create payload without branch_id first, then add it
    data = payload.model_dump()
    data["branch_id"] = branch_id
    department = Department(**data)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, payload: DepartmentCreate, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    department = department_service.get(db, department_id, branch_id)
    
    # Check if a department with the same name exists in the same branch (but not the same department)
    query = db.query(Department).filter(
        Department.name == payload.name, 
        Department.id != department_id, 
        Department.branch_id == branch_id
    )
    existing = query.first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="القسم موجود بالفعل في هذا الفرع.")
    
    # Update fields
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(department, key, value)
    department.branch_id = branch_id
    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    department = department_service.get(db, department_id, branch_id)
    # Set department_id to null for all employees in this department and branch
    db.query(Employee).filter(
        Employee.department_id == department_id, 
        Employee.branch_id == branch_id
    ).update({"department_id": None})
    db.delete(department)
    db.commit()
