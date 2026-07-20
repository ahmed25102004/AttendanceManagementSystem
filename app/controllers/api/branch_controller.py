from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_branch_manager_or_admin, get_db, get_current_branch_id, resolve_branch_scope
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.services.branch_service import BranchService


router = APIRouter()
branch_service = BranchService()


from fastapi import Query

@router.get("", response_model=list[BranchResponse], dependencies=[Depends(get_branch_manager_or_admin)])
def list_branches(
    db: Session = Depends(get_db), 
    current_user=Depends(get_branch_manager_or_admin),
    branch_id: int | None = Depends(get_current_branch_id), 
    all: bool = Query(False, description="Return all branches regardless of current branch selection")
):
    scoped_branch_id = resolve_branch_scope(current_user, branch_id, all)
    if scoped_branch_id:
        return [branch_service.get(db, scoped_branch_id)]
    return branch_service.list(db)


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_user)])
def create_branch(payload: BranchCreate, db: Session = Depends(get_db)):
    return branch_service.create(db, payload)


@router.get("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(get_branch_manager_or_admin)])
def get_branch(branch_id: int, db: Session = Depends(get_db)):
    return branch_service.get(db, branch_id)


@router.get("/{branch_id}/stats", dependencies=[Depends(get_branch_manager_or_admin)])
def get_branch_stats(branch_id: int, db: Session = Depends(get_db)):
    return branch_service.get_stats(db, branch_id)


@router.get("/all/stats", dependencies=[Depends(get_admin_user)])
def get_all_branches_stats(db: Session = Depends(get_db)):
    return branch_service.get_all_stats(db)


@router.put("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(get_admin_user)])
def update_branch(branch_id: int, payload: BranchUpdate, db: Session = Depends(get_db)):
    return branch_service.update(db, branch_id, payload)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_user)])
def delete_branch(branch_id: int, db: Session = Depends(get_db)):
    branch_service.delete(db, branch_id)
