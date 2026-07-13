from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db, get_current_branch_id
from app.services.export_service import ExportService
from app.services.report_service import ReportService


router = APIRouter(dependencies=[Depends(get_admin_user)])
report_service = ReportService()
export_service = ExportService()


@router.get("/daily")
def daily_report(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return report_service.daily_report(db, report_date, branch_id)


@router.get("/weekly")
def weekly_report(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return report_service.weekly_report(db, report_date, branch_id)


@router.get("/monthly")
def monthly_report(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return report_service.monthly_report(db, month, branch_id)


@router.get("/daily/export/excel")
def export_daily_excel(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.daily_report(db, report_date, branch_id)
    file_stream = export_service.export_excel(f"تقرير الحضور اليومي - {report_date.isoformat()}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="daily-report-{report_date.isoformat()}.xlsx"'},
    )


@router.get("/daily/export/pdf")
def export_daily_pdf(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.daily_report(db, report_date, branch_id)
    file_stream = export_service.export_pdf(f"تقرير الحضور اليومي - {report_date.isoformat()}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="daily-report-{report_date.isoformat()}.pdf"'},
    )


@router.get("/weekly/export/excel")
def export_weekly_excel(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.weekly_report(db, report_date, branch_id)
    file_stream = export_service.export_excel(f"تقرير الحضور الأسبوعي - {report_date.isoformat()}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="weekly-report-{report_date.isoformat()}.xlsx"'},
    )


@router.get("/weekly/export/pdf")
def export_weekly_pdf(report_date: date = Query(...), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.weekly_report(db, report_date, branch_id)
    file_stream = export_service.export_pdf(f"تقرير الحضور الأسبوعي - {report_date.isoformat()}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="weekly-report-{report_date.isoformat()}.pdf"'},
    )


@router.get("/monthly/export/excel")
def export_monthly_excel(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.monthly_report(db, month, branch_id)
    file_stream = export_service.export_excel(f"تقرير الحضور الشهري - {month}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="monthly-report-{month}.xlsx"'},
    )


@router.get("/monthly/export/pdf")
def export_monthly_pdf(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    rows = report_service.monthly_report(db, month, branch_id)
    file_stream = export_service.export_pdf(f"تقرير الحضور الشهري - {month}", rows)
    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="monthly-report-{month}.pdf"'},
    )
