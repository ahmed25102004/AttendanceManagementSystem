from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    branch_id: int | None = Field(default=None)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class DepartmentUpdate(BaseModel):
    branch_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class DepartmentResponse(DepartmentCreate):
    id: int

    class Config:
        from_attributes = True
