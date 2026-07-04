from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_db
from app.services.backup_service import BackupService


router = APIRouter(dependencies=[Depends(get_admin_user)])
backup_service = BackupService()


@router.post("/")
async def create_backup(db: Session = Depends(get_db)):
    backup_path = backup_service.create_backup(db)
    return {
        "status": "success",
        "path": backup_path
    }


@router.get("/")
async def list_backups():
    backups = backup_service.list_backups()
    return backups


@router.get("/download/{filename}")
async def download_backup(filename: str):
    import os
    backup_path = os.path.join(backup_service.backup_dir, filename)
    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="النسخة الاحتياطية غير موجودة"
        )
        
    return FileResponse(
        path=backup_path,
        media_type="application/json",
        filename=filename
    )


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_content = await file.read()
    backup_service.restore_backup(db, file_content)
    
    return {"status": "success", "message": "تمت استعادة النسخة الاحتياطية بنجاح"}


@router.delete("/{filename}", status_code=204)
async def delete_backup(filename: str):
    backup_service.delete_backup(filename)
