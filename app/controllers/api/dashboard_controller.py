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


@router.get("/kpis")
def overall_kpis(db: Session = Depends(get_db)):
    return dashboard_service.get_overall_kpis(db)


@router.get("/branches-stats")
def branches_stats(db: Session = Depends(get_db)):
    return dashboard_service.get_branches_stats(db)


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    return dashboard_service.get_alerts(db)


@router.get("/recent-logs")
def recent_logs(db: Session = Depends(get_db)):
    return dashboard_service.get_recent_logs(db)
