from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_branch_manager_or_admin, get_db, get_required_branch_id
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceTestResponse
from app.services.device_service import DeviceService

router = APIRouter(dependencies=[Depends(get_branch_manager_or_admin)])
device_service = DeviceService()


@router.get("", response_model=list[DeviceResponse])
def list_devices(
    search: str | None = Query(None),
    status: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id),
    all: bool = Query(False, description="Return all devices regardless of current branch selection")
):
    devices = device_service.list(db, None if all else branch_id, search, status, is_active)
    responses = []
    for device in devices:
        resp = DeviceResponse.model_validate(device)
        resp.log_count = device_service.get_log_count(db, device.id)
        responses.append(resp)
    return responses


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    device = device_service.get(db, device_id, branch_id)
    resp = DeviceResponse.model_validate(device)
    resp.log_count = device_service.get_log_count(db, device.id)
    return resp


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate, 
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id)
):
    # Set branch_id automatically if not provided
    if not payload.branch_id:
        payload.branch_id = branch_id
    return device_service.create(db, payload)


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int, 
    payload: DeviceUpdate, 
    db: Session = Depends(get_db),
    branch_id: int = Depends(get_required_branch_id)
):
    # Set branch_id automatically if not provided
    if not payload.branch_id:
        payload.branch_id = branch_id
    return device_service.update(db, device_id, payload, branch_id)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    device_service.delete(db, device_id, branch_id)


@router.post("/{device_id}/test", response_model=DeviceTestResponse)
def test_device_connection(device_id: int, db: Session = Depends(get_db), branch_id: int = Depends(get_required_branch_id)):
    success, message = device_service.test_connection(db, device_id, branch_id)
    return {"success": success, "message": message}
