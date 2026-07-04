from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.schemas.report import DashboardSummary
from app.services.dashboard_service import DashboardService


router = APIRouter(dependencies=[Depends(get_admin_user)])
dashboard_service = DashboardService()


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    return dashboard_service.get_summary(db)
