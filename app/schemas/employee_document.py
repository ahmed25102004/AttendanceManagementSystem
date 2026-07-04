from datetime import datetime
from pydantic import BaseModel, Field


class EmployeeDocumentBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: str | None = None


class EmployeeDocumentCreate(EmployeeDocumentBase):
    employee_id: int


class EmployeeDocumentUpdate(EmployeeDocumentBase):
    pass


class EmployeeDocumentResponse(EmployeeDocumentBase):
    id: int
    employee_id: int
    file_path: str
    file_type: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
