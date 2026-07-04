from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.task import Task
from app.models.employee import Employee
from app.models.user import User
from app.models.notification import Notification
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def _get_employee_full_name(self, employee: Employee | None) -> str | None:
        if not employee:
            return None
        return " ".join(
            part.strip() for part in [employee.first_name, employee.last_name] if part and part.strip()
        )
        
    def _send_notification(self, db: Session, user_id: int, title: str, message: str) -> None:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message
        )
        db.add(notification)

    def create(self, db: Session, payload: TaskCreate, current_user_id: int) -> Task:
        employee = db.query(Employee).filter(Employee.id == payload.assigned_to).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الموظف غير موجود."
            )
            
        task = Task(
            **payload.model_dump(),
            created_by=current_user_id
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Notify assigned employee
        if employee.user:
            self._send_notification(
                db,
                employee.user.id,
                "مهمة جديدة",
                f"لديك مهمة جديدة: {payload.title}"
            )
            db.commit()
        
        task.assigned_to_name = self._get_employee_full_name(employee)
        return task

    def list(self, db: Session, employee_id: int | None = None) -> list[Task]:
        query = db.query(Task).options(
            joinedload(Task.assigned_employee),
            joinedload(Task.creator)
        )
        
        if employee_id:
            query = query.filter(Task.assigned_to == employee_id)
        
        tasks = query.order_by(Task.created_at.desc()).all()
        
        for task in tasks:
            task.assigned_to_name = self._get_employee_full_name(task.assigned_employee)
            task.created_by_name = task.creator.full_name if task.creator else None
            
        return tasks

    def get(self, db: Session, task_id: int) -> Task:
        task = db.query(Task).options(
            joinedload(Task.assigned_employee),
            joinedload(Task.creator)
        ).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المهمة غير موجودة."
            )
            
        task.assigned_to_name = self._get_employee_full_name(task.assigned_employee)
        task.created_by_name = task.creator.full_name if task.creator else None
        return task

    def update(self, db: Session, task_id: int, payload: TaskUpdate) -> Task:
        task = self.get(db, task_id)
        
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        
        # Notify employee if status changed or re-assigned
        if payload.status or payload.assigned_to:
            employee = db.query(Employee).filter(Employee.id == task.assigned_to).first()
            if employee and employee.user:
                status_text = {
                    "pending": "قيد الانتظار",
                    "in_progress": "قيد التنفيذ",
                    "completed": "مكتملة",
                    "cancelled": "ملغاة"
                }
                self._send_notification(
                    db,
                    employee.user.id,
                    "تحديث المهمة",
                    f"تم تحديث حالة المهمة '{task.title}' إلى {status_text.get(task.status, task.status)}"
                )
                db.commit()
        
        task.assigned_to_name = self._get_employee_full_name(task.assigned_employee)
        task.created_by_name = task.creator.full_name if task.creator else None
        return task

    def delete(self, db: Session, task_id: int) -> None:
        task = self.get(db, task_id)
        db.delete(task)
        db.commit()
