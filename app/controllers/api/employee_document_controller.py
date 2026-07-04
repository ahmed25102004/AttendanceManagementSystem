from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.dependencies import get_admin_user, get_db
from app.schemas.employee_document import EmployeeDocumentCreate, EmployeeDocumentResponse
from app.services.employee_document_service import EmployeeDocumentService


router = APIRouter(dependencies=[Depends(get_admin_user)])
document_service = EmployeeDocumentService()


@router.get("/employee/{employee_id}", response_model=list[EmployeeDocumentResponse])
def get_employee_documents(employee_id: int, db: Session = Depends(get_db)):
    return document_service.list_for_employee(db, employee_id)


@router.post("/", response_model=EmployeeDocumentResponse, status_code=201)
async def upload_document(
    employee_id: int = Form(...),
    name: str = Form(...),
    notes: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_content = await file.read()
    payload = EmployeeDocumentCreate(
        employee_id=employee_id,
        name=name,
        notes=notes
    )
    return document_service.create(db, payload, file_content, file.filename, file.content_type)


@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db)):
    doc = document_service.get(db, document_id)
    file_path = Path(doc.file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الملف غير موجود"
        )
        
    return FileResponse(
        path=str(file_path),
        media_type=doc.file_type,
        filename=doc.name
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document_service.delete(db, document_id)
