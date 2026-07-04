from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_employee_user, get_db, get_current_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import TaskService


router = APIRouter()
task_service = TaskService()


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role == "employee":
        return task_service.list(db, current_user.employee_id)
    return task_service.list(db)


@router.post("", response_model=TaskResponse, status_code=201, dependencies=[Depends(get_admin_user)])
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return task_service.create(db, payload, current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return task_service.get(db, task_id)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return task_service.update(db, task_id, payload)


@router.delete("/{task_id}", status_code=204, dependencies=[Depends(get_admin_user)])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    return task_service.delete(db, task_id)
