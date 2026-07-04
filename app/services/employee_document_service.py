import os
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.employee_document import EmployeeDocument
from app.schemas.employee_document import EmployeeDocumentCreate, EmployeeDocumentUpdate


class EmployeeDocumentService:
    def __init__(self):
        self.upload_dir = "uploads/employee_documents"
        os.makedirs(self.upload_dir, exist_ok=True)
        
    def create(self, db: Session, payload: EmployeeDocumentCreate, file_content: bytes, file_name: str, content_type: str) -> EmployeeDocument:
        # Create a unique filename
        import uuid
        ext = os.path.splitext(file_name)[1] or ""
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        # Save to database
        doc = EmployeeDocument(
            employee_id=payload.employee_id,
            name=payload.name,
            file_path=file_path,
            file_type=content_type,
            notes=payload.notes
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        return doc
        
    def list_for_employee(self, db: Session, employee_id: int) -> list[EmployeeDocument]:
        return db.query(EmployeeDocument).filter(EmployeeDocument.employee_id == employee_id).order_by(EmployeeDocument.uploaded_at.desc()).all()
        
    def get(self, db: Session, document_id: int) -> EmployeeDocument:
        doc = db.query(EmployeeDocument).filter(EmployeeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستند غير موجود"
            )
        return doc
        
    def delete(self, db: Session, document_id: int) -> None:
        doc = self.get(db, document_id)
        
        # Delete file from disk
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            
        db.delete(doc)
        db.commit()
