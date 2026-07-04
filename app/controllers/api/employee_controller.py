from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.employee_service import EmployeeService


router = APIRouter(dependencies=[Depends(get_admin_user)])
employee_service = EmployeeService()


@router.get("", response_model=list[EmployeeResponse])
def list_employees(search: str | None = Query(default=None), db: Session = Depends(get_db)):
    return employee_service.list(db, search)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    return employee_service.create(db, payload)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db)):
    return employee_service.update(db, employee_id, payload)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee_service.delete(db, employee_id)
