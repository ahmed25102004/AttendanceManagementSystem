from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.leave import Leave, LeaveStatus, LeaveType
from app.models.employee import Employee
from app.models.user import User
from app.models.notification import Notification
from app.schemas.leave import LeaveCreate, LeaveUpdate


class LeaveService:
    def _count_leave_days(self, start_date: date, end_date: date) -> int:
        days = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday only
                days += 1
            current_date += timedelta(days=1)
        return days

    def _get_employee_full_name(self, employee: Employee) -> str:
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

    def create(self, db: Session, payload: LeaveCreate) -> Leave:
        if payload.start_date > payload.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تاريخ البداية يجب أن يكون قبل تاريخ النهاية.",
            )
        
        if payload.start_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن طلب اجازة بتاريخ سابق.",
            )

        employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الموظف غير موجود.",
            )
        
        leave_days = self._count_leave_days(payload.start_date, payload.end_date)
        
        if payload.type == LeaveType.ANNUAL and leave_days > employee.annual_leave_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"رصيد اجازاتك السنوية لا يكفي. لديك {employee.annual_leave_balance} يوم فقط.",
            )
        if payload.type == LeaveType.SICK and leave_days > employee.sick_leave_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"رصيد اجازاتك المرضية لا يكفي. لديك {employee.sick_leave_balance} يوم فقط.",
            )

        leave = Leave(**payload.model_dump())
        db.add(leave)
        db.commit()
        db.refresh(leave)
        
        # Notify admins about new leave request
        admins = db.query(User).filter(User.role == "admin").all()
        for admin in admins:
            self._send_notification(
                db,
                admin.id,
                "طلب اجازة جديد",
                f"طلب اجازة من {self._get_employee_full_name(employee)} في الفترة من {payload.start_date} إلى {payload.end_date}"
            )
        db.commit()
        
        leave.employee_name = self._get_employee_full_name(employee)
        return leave

    def list(self, db: Session, employee_id: int | None = None) -> list[Leave]:
        query = db.query(Leave).options(joinedload(Leave.employee))
        
        if employee_id:
            query = query.filter(Leave.employee_id == employee_id)
        
        leaves = query.order_by(Leave.id.desc()).all()
        
        for leave in leaves:
            leave.employee_name = self._get_employee_full_name(leave.employee)
        
        return leaves

    def get(self, db: Session, leave_id: int) -> Leave:
        leave = db.query(Leave).options(joinedload(Leave.employee)).filter(Leave.id == leave_id).first()
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الطلب غير موجود.",
            )
        leave.employee_name = self._get_employee_full_name(leave.employee)
        return leave

    def update(self, db: Session, leave_id: int, payload: LeaveUpdate) -> Leave:
        leave = self.get(db, leave_id)
        
        if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تاريخ البداية يجب أن يكون قبل تاريخ النهاية.",
            )

        if payload.status and leave.status != LeaveStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن تعديل طلب تمت الموافقة عليه أو رفضه.",
            )
        
        if payload.status and payload.status == LeaveStatus.APPROVED:
            employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
            leave_days = self._count_leave_days(
                payload.start_date or leave.start_date,
                payload.end_date or leave.end_date
            )
            
            if leave.type == LeaveType.ANNUAL:
                employee.annual_leave_balance -= leave_days
            elif leave.type == LeaveType.SICK:
                employee.sick_leave_balance -= leave_days
        
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(leave, key, value)
        
        db.commit()
        db.refresh(leave)
        
        # Notify employee about status change
        if payload.status:
            employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
            if employee.user:
                status_text = "مقبول" if payload.status == LeaveStatus.APPROVED else "مرفوض"
                self._send_notification(
                    db,
                    employee.user.id,
                    "تحديث حالة طلب الأجازة",
                    f"تم {status_text} طلب الأجازة الخاص بك في الفترة من {leave.start_date} إلى {leave.end_date}"
                )
                db.commit()
        
        leave.employee_name = self._get_employee_full_name(leave.employee)
        return leave

    def delete(self, db: Session, leave_id: int) -> None:
        leave = self.get(db, leave_id)
        if leave.status != LeaveStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن حذف طلب تمت الموافقة عليه أو رفضه.",
            )
        db.delete(leave)
        db.commit()
