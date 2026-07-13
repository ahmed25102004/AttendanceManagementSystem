from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import logging

from app.core.dependencies import get_db
from app.models.device import Device
from app.services.device_service import DeviceService
from app.services.attendance_log_service import AttendanceLogService

router = APIRouter()
device_service = DeviceService()
attendance_log_service = AttendanceLogService()

logger = logging.getLogger(__name__)

# ZKTeco ADMS responses
OK_RESPONSE = "OK"
ERROR_RESPONSE = "ERROR"


def parse_attendance_type(status_code: str | None) -> str:
    # Map ZKTeco status codes to our types
    mapping = {
        "0": "check_in",
        "1": "check_out",
        "2": "break_in",
        "3": "break_out",
        "4": "ot_in",
        "5": "ot_out"
    }
    return mapping.get(str(status_code) if status_code else "0", "check_in")


def parse_verify_type(verify_code: str | None) -> str:
    mapping = {
        "0": "password",
        "1": "fingerprint",
        "2": "card",
        "3": "face"
    }
    return mapping.get(str(verify_code) if verify_code else "1", "fingerprint")


@router.get("/cdata")
@router.get("/heartbeat")
async def handle_heartbeat(request: Request, db: Session = Depends(get_db)):
    # Handle device heartbeat
    sn = request.query_params.get("SN")
    if not sn:
        logger.warning("Heartbeat received without SN")
        return PlainTextResponse(ERROR_RESPONSE)
    
    logger.info(f"Received heartbeat from SN: {sn}")
    
    # Try to find device by device_code first
    device = device_service.get_by_device_code(db, sn)
    if not device:
        logger.info(f"Device not found by device_code={sn}, trying serial_number")
        device = device_service.get_by_serial_number(db, sn)
    if not device:
        all_devices = db.query(Device).all()
        device_info = [f"id={d.id}, device_code={d.device_code}, serial_number={d.serial_number}" for d in all_devices]
        logger.warning(f"Unknown device with SN {sn}. All devices: {device_info}")
        return PlainTextResponse(ERROR_RESPONSE)
    
    if not device.is_active:
        logger.warning(f"Device {sn} is inactive")
        return PlainTextResponse(ERROR_RESPONSE)
    
    logger.info(f"Heartbeat successful for device id={device.id}, name={device.device_name}")
    # Update last seen
    device_service.update_last_seen(db, device.id)
    return PlainTextResponse(OK_RESPONSE)


@router.post("/cdata")
async def handle_cdata(request: Request, db: Session = Depends(get_db)):
    # Handle attendance data
    try:
        form_data = await request.form()
        # Log all form data for debugging
        logger.info(f"Received cdata: {dict(form_data)}")
        
        # Extract device SN
        sn = form_data.get("SN") or form_data.get("sn")
        if not sn:
            logger.warning("cdata received without SN")
            return PlainTextResponse(ERROR_RESPONSE)
        
        logger.info(f"Received cdata from SN: {sn}")
        
        # Try to find device by device_code first
        device = device_service.get_by_device_code(db, sn)
        if not device:
            logger.info(f"Device not found by device_code={sn}, trying serial_number")
            device = device_service.get_by_serial_number(db, sn)
        if not device:
            logger.warning(f"Unknown device with SN {sn}. All devices: {[d.device_code for d in db.query(device_service.model).all()]}")
            return PlainTextResponse(ERROR_RESPONSE)
        
        if not device.is_active:
            return PlainTextResponse(ERROR_RESPONSE)
        
        # Update last seen
        device_service.update_last_seen(db, device.id)
        
        # Process attendance records
        table = form_data.get("table")
        if table and "ATTLOG" in table.upper():
            # The data is in "ATTLOG" format
            records = form_data.get("records") or ""
            for line in records.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Parse log line (usually tab or comma separated)
                # Sample line format: PIN\tTime\tStatus\tVerifyCode\tWorkCode
                parts = line.split("\t") if "\t" in line else line.split(",")
                if len(parts) < 2:
                    continue
                
                pin = parts[0].strip()
                time_str = parts[1].strip()
                status = parts[2].strip() if len(parts) > 2 else "0"
                verify = parts[3].strip() if len(parts) > 3 else "1"
                
                try:
                    check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        check_time = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                    except Exception:
                        logger.warning(f"Invalid time format: {time_str}")
                        continue
                
                try:
                    attendance_log_service.create(
                        db=db,
                        device=device,
                        employee_code=pin,
                        check_time=check_time,
                        attendance_type=parse_attendance_type(status),
                        verify_type=parse_verify_type(verify),
                        raw_data={"raw_line": line},
                        record_id=f"{device.device_code or device.serial_number}-{pin}-{time_str}"
                    )
                except HTTPException as e:
                    if e.status_code != 409:  # Ignore duplicates
                        logger.error(f"Error processing log: {e}")
        return PlainTextResponse(OK_RESPONSE)
    except Exception as e:
        logger.exception("Error processing cdata request")
        return PlainTextResponse(ERROR_RESPONSE)


@router.get("/getinfo")
async def handle_getinfo(request: Request, db: Session = Depends(get_db)):
    # Return device info
    return PlainTextResponse("Ret=0")


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def handle_other_requests(request: Request, path: str, db: Session = Depends(get_db)):
    # Handle other ADMS requests (like gettime, setuser, etc.)
    logger.info(f"Received request to /{path}: {request.method} {dict(request.query_params)}")
    if request.method == "POST":
        try:
            logger.info(f"POST body: {await request.form()}")
        except Exception:
            pass
    return PlainTextResponse(OK_RESPONSE)
