from datetime import datetime
from fastapi import APIRouter, Depends, Request
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


def log_request(prefix: str, request: Request):
    logger.info(f"[{prefix}] {request.method} {request.url.path} - Params: {dict(request.query_params)}")


def get_sn(request: Request) -> str | None:
    params = dict(request.query_params)
    return params.get("SN") or params.get("sn")


def get_device(db: Session, sn: str):
    device = device_service.get_by_device_code(db, sn)
    if not device:
        device = device_service.get_by_serial_number(db, sn)
    return device


@router.get("/getrequest")
async def handle_getrequest(request: Request, db: Session = Depends(get_db)):
    """
    Heartbeat endpoint - device polls for commands
    """
    log_request("GETREQUEST", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
            logger.info(f"[GETREQUEST] Device {sn} connected")
    # Always return empty for no commands pending
    return PlainTextResponse("")


@router.get("/getinfo")
async def handle_getinfo(request: Request, db: Session = Depends(get_db)):
    """Return device info response"""
    log_request("GETINFO", request)
    return PlainTextResponse("Ret=0")


@router.get("/gettime")
async def handle_gettime(request: Request, db: Session = Depends(get_db)):
    """Return current time for sync"""
    log_request("GETTIME", request)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return PlainTextResponse(f"Ret=0\nTime={now}")


@router.get("/cdata")
async def handle_cdata_get(request: Request, db: Session = Depends(get_db)):
    """
    Handle GET /iclock/cdata - this is the INITIAL HANDSHAKE when options=all!
    This is the MOST CRITICAL PART - this tells the device to send attendance!
    """
    log_request("CDATA-GET", request)
    params = dict(request.query_params)
    sn = get_sn(request)
    options = params.get("options")

    # If this is an initial handshake (options=all or similar), respond with proper config!
    if options and ("all" in options or "options" in options):
        if not sn:
            logger.warning("[CDATA-GET] Handshake missing SN")
            return PlainTextResponse("ERROR")

        # Find device first
        device = get_device(db, sn)
        if not device:
            logger.error(f"[CDATA-GET] Unknown device SN: {sn}")
            return PlainTextResponse("ERROR")

        # Update last seen immediately
        device_service.update_last_seen(db, device.id)

        # Build the FULL CONFIG RESPONSE the device is expecting!
        # Follow the exact format from admsjs PROTOCOL.md and StandTech docs
        response_lines = [
            f"GET OPTION FROM: {sn}",
            "ATTLOGStamp=0",
            "OPERLOGStamp=0",
            "BIODATAStamp=0",
            "ATTPHOTOStamp=0",
            "ErrorDelay=10",
            "Delay=5",
            "TransTimes=00:00;23:59",
            "TransInterval=1",
            "TransFlag=TransData AttLog OpLog EnrollUser ChgUser EnrollFP ChgFP FPImag",
            "Realtime=1",  # THIS IS KEY - ENABLE REAL-TIME UPLOAD!
            "ServerVer=3.0.1",  # MUST BE PRESENT!
            "PushProtVer=2.4.1",  # Protocol version
            "TimeZone=0",  # Or adjust for your timezone
            "SupportPing=1"
        ]

        # Join with CRLF and return as plain text
        response_body = "\r\n".join(response_lines)
        logger.info(f"[CDATA-GET] Handshake response sent: {response_body}")
        return PlainTextResponse(response_body, media_type="text/plain")

    # Otherwise, treat as a heartbeat
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")


@router.post("/cdata")
async def handle_cdata_post(request: Request, db: Session = Depends(get_db)):
    """Handle incoming data uploads from device"""
    log_request("CDATA-POST", request)
    try:
        form_data = await request.form()
        logger.info(f"[CDATA-POST] Form data received: {dict(form_data)}")
        raw_body = await request.body()
        logger.info(f"[CDATA-POST] Raw body: {raw_body.decode('utf-8', errors='replace')}")
    except Exception as e:
        raw_body = await request.body()
        logger.warning(f"[CDATA-POST] Failed to parse form data: {e}")
        logger.info(f"[CDATA-POST] Raw body (non-form): {raw_body.decode('utf-8', errors='replace')}")
        form_data = {}

    params = dict(request.query_params)
    sn = get_sn(request)
    if not sn:
        # Also try to get from form data
        sn = form_data.get("SN") or form_data.get("sn")

    if not sn:
        logger.warning("[CDATA-POST] Missing SN")
        return PlainTextResponse("ERROR")

    device = get_device(db, sn)
    if not device:
        logger.error(f"[CDATA-POST] Unknown device SN: {sn}")
        return PlainTextResponse("ERROR")

    # Update last seen and sync timestamps
    device_service.update_last_seen(db, device.id)
    device_service.update_last_sync(db, device.id)

    table = params.get("table") or form_data.get("table")
    logger.info(f"[CDATA-POST] Incoming table data: {table}")

    # Process ATTLOG table
    if table and "ATTLOG" in table.upper():
        records_text = params.get("records") or form_data.get("records")
        if records_text:
            logger.info(f"[CDATA-POST] Processing ATTLOG records: {records_text}")
            for line in records_text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Split line by tabs (standard format)
                parts = line.split("\t")
                if len(parts) < 2:
                    # Try split by commas as backup
                    parts = line.split(",")

                if len(parts) < 2:
                    continue

                pin = parts[0].strip()
                time_str = parts[1].strip()
                status = parts[2].strip() if len(parts) > 2 else "0"
                verify = parts[3].strip() if len(parts) > 3 else "1"

                try:
                    # Try parsing time in various formats
                    try:
                        check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            check_time = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                        except ValueError:
                            logger.warning(f"Could not parse time: {time_str}")
                            continue

                    # Create the attendance log
                    attendance_log_service.create(
                        db=db,
                        device=device,
                        employee_code=pin,
                        check_time=check_time,
                        attendance_type=str(status),
                        verify_type=str(verify),
                        raw_data={"raw_line": line},
                        record_id=f"{device.device_code or device.serial_number}-{pin}-{time_str}"
                    )
                    logger.info(f"Successfully processed attendance: PIN={pin}, Time={time_str}")
                except Exception as e:
                    logger.error(f"Failed to process attendance line: {line}, error: {e}")

    logger.info(f"[CDATA-POST] Done processing, returning OK")
    return PlainTextResponse("OK")


# Handle all other endpoints for compatibility
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_other_requests(request: Request, db: Session = Depends(get_db)):
    log_request(f"OTHER-{request.method}", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")
