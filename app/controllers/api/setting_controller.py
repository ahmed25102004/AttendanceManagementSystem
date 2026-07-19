from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_current_branch_id
from app.core.database import SessionLocal
from app.schemas.setting import CompanySettingResponse, CompanySettingUpdate
from app.services.backup_service import BackupService
from app.services.setting_service import SettingService
from app.services.zkteco_service import ZKTecoService


router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])
setting_service = SettingService()
backup_service = BackupService()


def update_scheduler_job():
    # Avoid circular import - import scheduler locally
    from app.main import scheduler
    
    # Remove existing jobs if they exist
    if scheduler.get_job("daily_backup"):
        scheduler.remove_job("daily_backup")
    if scheduler.get_job("zkteco_sync"):
        scheduler.remove_job("zkteco_sync")
    
    # Get settings
    db = SessionLocal()
    try:
        settings_obj = setting_service.get_settings(db)
        
        # Schedule daily backup
        if settings_obj.auto_backup_enabled:
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
        
        # Schedule ZKTeco auto-sync
        if hasattr(settings_obj, 'zkteco_auto_sync_enabled') and settings_obj.zkteco_auto_sync_enabled:
            def scheduled_zkteco_sync():
                try:
                    zkteco_db = SessionLocal()
                    try:
                        zkteco_service = ZKTecoService(zkteco_db)
                        zkteco_service.sync_attendance_logs()
                    finally:
                        zkteco_db.close()
                except Exception as e:
                    import logging
                    logging.error(f"Error in scheduled ZKTeco sync: {str(e)}")
            
            interval_minutes = settings_obj.zkteco_auto_sync_interval_minutes if hasattr(settings_obj, 'zkteco_auto_sync_interval_minutes') else 30
            scheduler.add_job(
                scheduled_zkteco_sync,
                'interval',
                minutes=interval_minutes,
                id='zkteco_sync',
                replace_existing=True
            )
    finally:
        db.close()


@router.get("", response_model=CompanySettingResponse)
def get_settings(db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    return setting_service.get_settings(db, branch_id)


@router.put("", response_model=CompanySettingResponse)
def update_settings(payload: CompanySettingUpdate, db: Session = Depends(get_db), branch_id: int | None = Depends(get_current_branch_id)):
    print("[DEBUG] PUT /api/settings payload:", payload.model_dump())
    result = setting_service.update_settings(db, payload, branch_id)
    update_scheduler_job()
    return result
