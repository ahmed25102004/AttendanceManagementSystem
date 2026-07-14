from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import logging
import time

from app.core.dependencies import get_db
from app.models.device import Device
from app.services.device_service import DeviceService
from app.services.attendance_log_service import AttendanceLogService

router = APIRouter()
device_service = DeviceService()
attendance_log_service = AttendanceLogService()

logger = logging.getLogger(__name__)

# ZKTeco ADMS standard responses
OK_RESPONSE = "OK"
ERROR_RESPONSE = "ERROR"
GETREQUEST_RESPONSE = ""  # Empty means no commands pending


def parse_attendance_type(status_code: str | None) -> str:
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


def log_full_request(request: Request, stage: str = "request"):
    logger.info(f"[{stage}] METHOD={request.method} URL={request.url} PARAMS={dict(request.query_params)}")


@router.get("/cdata")
@router.get("/heartbeat")
@router.get("")
async def handle_heartbeat(request: Request, db: Session = Depends(get_db)):
    log_full_request(request, "HEARTBEAT")
    sn = request.query_params.get("SN") or request.query_params.get("sn")
    if not sn:
        logger.warning("Heartbeat received without SN")
        return PlainTextResponse(ERROR_RESPONSE)
    
    logger.info(f"[HEARTBEAT] Received SN: '{sn}'")
    
    device = device_service.get_by_device_code(db, sn)
    if not device:
        device = device_service.get_by_serial_number(db, sn)
    
    if not device:
        logger.error(f"[HEARTBEAT] Unknown device SN={sn}")
        return PlainTextResponse(ERROR_RESPONSE)
    
    if not device.is_active:
        logger.warning(f"[HEARTBEAT] Device {sn} inactive")
        return PlainTextResponse(ERROR_RESPONSE)
    
    logger.info(f"[HEARTBEAT] Success for {device.device_name}")
    device_service.update_last_seen(db, device.id)
    return PlainTextResponse(OK_RESPONSE)


@router.post("/cdata")
@router.post("")
async def handle_cdata(request: Request, db: Session = Depends(get_db)):
    start_time = time.time()
    log_full_request(request, "CDATA")
    
    try:
        form_data = None
        raw_body = None
        
        try:
            form_data = await request.form()
            raw_body = str(dict(form_data))
        except Exception:
            raw_body = (await request.body()).decode('utf-8', errors='replace')
        
        logger.info(f"[CDATA] DATA: {raw_body}")
        
        sn = form_data.get("SN") if form_data else None
        if not sn:
            sn = request.query_params.get("SN") or request.query_params.get("sn")
            
        if not sn:
            logger.warning("[CDATA] No SN received")
            return PlainTextResponse(ERROR_RESPONSE)
        
        device = device_service.get_by_device_code(db, sn)
        if not device:
            device = device_service.get_by_serial_number(db, sn)
            
        if not device:
            logger.error(f"[CDATA] Unknown device: {sn}")
            return PlainTextResponse(ERROR_RESPONSE)
            
        device_service.update_last_seen(db, device.id)
        
        if form_data:
            table = form_data.get("table")
            
            if table and "ATTLOG" in table.upper():
                records = form_data.get("records", "")
                logger.info(f"[CDATA] Processing ATTLOG: {records}")
                
                for line in records.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                        
                    parts = line.split("\t") if "\t" in line else line.split(",")
                    if len(parts) <2:
                        continue
                        
                    pin = parts[0].strip()
                    time_str = parts[1].strip()
                    att_status = parts[2].strip() if len(parts) > 2 else "0"
                    verify = parts[3].strip() if len(parts) >3 else "1"
                    
                    try:
                        check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            check_time = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                        except Exception as e:
                            logger.warning(f"Invalid time: {time_str} - {e}")
                            continue
                            
                    try:
                        attendance_log = attendance_log_service.create(
                            db=db,
                            device=device,
                            employee_code=pin,
                            check_time=check_time,
                            attendance_type=parse_attendance_type(att_status),
                            verify_type=parse_verify_type(verify),
                            raw_data={"raw": line},
                            record_id=f"{device.device_code or device.serial_number}-{pin}-{time_str}"
                        )
                        logger.info(f"[CDATA] Saved log saved: {pin} at {check_time}")
                    except HTTPException as e:
                        if e.status_code != 409:
                            logger.error(f"Error processing log: {e}")
                
        process_time = round(time.time() - start_time)
        logger.info(f"[CDATA] Processed in: {process_time:.2f}s")
        return PlainTextResponse(OK_RESPONSE)
    except Exception as e:
        logger.exception("[CDATA] Fatal error")
        return PlainTextResponse(ERROR_RESPONSE)


@router.get("/getinfo")
async def handle_getinfo(request: Request, db: Session = Depends(get_db)):
    log_full_request(request, "GETINFO")
    return PlainTextResponse("Ret=0")


@router.get("/getrequest")
async def handle_getrequest(request: Request, db: Session = Depends(get_db)):
    """
    CRITICAL: This is the most important endpoint for ZKTeco ADMS!
    The device polls this endpoint to get commands!
    We return empty string to tell device to send pending data!
    """
    log_full_request(request, "GETREQUEST")
    sn = request.query_params.get("SN") or request.query_params.get("sn")
    if sn:
        device = device_service.get_by_device_code(db, sn)
        if not device:
            device = device_service.get_by_serial_number(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
            logger.info(f"[GETREQUEST] Device {sn} checked in")
    return PlainTextResponse(GETREQUEST_RESPONSE)


@router.get("/gettime")
async def handle_gettime(request: Request, db: Session = Depends(get_db)):
    """Return current time to device for time sync"""
    log_full_request(request, "GETTIME")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return PlainTextResponse(f"Ret=0\nTime={now}")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_other_requests(request: Request, path: str, db: Session = Depends(get_db)):
    log_full_request(request, f"OTHER:{path}")
    return PlainTextResponse(OK_RESPONSE)
