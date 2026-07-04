from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.core.database import SessionLocal
from app.schemas.setting import CompanySettingResponse, CompanySettingUpdate
from app.services.backup_service import BackupService
from app.services.setting_service import SettingService


router = APIRouter(dependencies=[Depends(get_admin_user)])
setting_service = SettingService()
backup_service = BackupService()


def update_scheduler_job():
    # Avoid circular import - import scheduler locally
    from app.main import scheduler
    
    # Remove existing job if exists
    if scheduler.get_job("daily_backup"):
        scheduler.remove_job("daily_backup")
    
    # Get settings
    db = SessionLocal()
    try:
        settings_obj = setting_service.get_settings(db)
        if settings_obj.auto_backup_enabled:
            # Schedule daily backup at the specified time
            def scheduled_backup():
                try:
                    backup_db = SessionLocal()
                    try:
                        backup_service.create_backup(backup_db)
                        backup_service.clean_old_backups(settings_obj.auto_backup_retention_days)
                    finally:
                        backup_db.close()
                except Exception as e:
                    import logging
                    logging.error(f"Error in scheduled backup: {str(e)}")
            
            scheduler.add_job(
                scheduled_backup,
                'cron',
                hour=settings_obj.auto_backup_time.hour,
                minute=settings_obj.auto_backup_time.minute,
                id='daily_backup',
                replace_existing=True
            )
    finally:
        db.close()


@router.get("", response_model=CompanySettingResponse)
def get_settings(db: Session = Depends(get_db)):
    return setting_service.get_settings(db)


@router.put("", response_model=CompanySettingResponse)
def update_settings(payload: CompanySettingUpdate, db: Session = Depends(get_db)):
    result = setting_service.update_settings(db, payload)
    update_scheduler_job()
    return result
