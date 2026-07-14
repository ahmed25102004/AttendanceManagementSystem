
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
    logger.info(f"[{prefix}] {request.method} {request.url}")
    params = dict(request.query_params)
    if params:
        logger.info(f"  Params: {params}")


def get_sn(request: Request) -> str | None:
    params = dict(request.query_params)
    return params.get("SN") or params.get("sn")


def get_device(db: Session, sn: str):
    device = device_service.get_by_device_code(db, sn)
    if not device:
        device = device_service.get_by_serial_number(db, sn)
    return device


@router.get("/test")
async def test_endpoint():
    return PlainTextResponse("NEW CODE IS RUNNING! SUCCESS!")


@router.get("/ping")
async def handle_ping(request: Request, db: Session = Depends(get_db)):
    log_request("PING", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
            logger.info(f"  Ping from device {sn} updated")
    return PlainTextResponse("OK")


@router.get("/getrequest")
async def handle_getrequest(request: Request, db: Session = Depends(get_db)):
    log_request("GETREQUEST", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
            logger.info(f"  Device {sn} polled, last seen updated")
    # Always empty command queue for now
    return PlainTextResponse("OK")


@router.get("/registry")
async def handle_registry(request: Request, db: Session = Depends(get_db)):
    log_request("REGISTRY", request)
    sn = get_sn(request)
    if not sn:
        logger.error("  Registry request missing SN, rejecting")
        return PlainTextResponse("ERROR")
    
    device = get_device(db, sn)
    if not device:
        logger.error(f"  Device {sn} not found in database, rejecting")
        return PlainTextResponse("ERROR")
    
    device_service.update_last_seen(db, device.id)
    # Return registry block as per Push SDK
    return PlainTextResponse(f"RegistryCode={sn}\r\n")


@router.post("/devicecmd")
async def handle_devicecmd(request: Request, db: Session = Depends(get_db)):
    log_request("DEVICECMD", request)
    sn = get_sn(request)
    if not sn:
        logger.error("  Devicecmd request missing SN, rejecting")
        return PlainTextResponse("ERROR")
    
    device = get_device(db, sn)
    if not device:
        logger.error(f"  Device {sn} not found in database, rejecting")
        return PlainTextResponse("ERROR")
    
    # Update last seen
    device_service.update_last_seen(db, device.id)
    
    # Log the command result
    try:
        form_data = await request.form()
        logger.info(f"  Form data: {dict(form_data)}")
        raw_body = await request.body()
        logger.info(f"  Raw body: {raw_body.decode('utf-8', errors='replace')}")
    except Exception as e:
        logger.error(f"  Error reading devicecmd request: {e}")
    
    return PlainTextResponse("OK")


@router.get("/getinfo")
async def handle_getinfo(request: Request, db: Session = Depends(get_db)):
    log_request("GETINFO", request)
    return PlainTextResponse("Ret=0")


@router.get("/gettime")
async def handle_gettime(request: Request, db: Session = Depends(get_db)):
    log_request("GETTIME", request)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return PlainTextResponse(f"Ret=0\nTime={now}")


@router.get("/cdata")
async def handle_cdata_get(request: Request, db: Session = Depends(get_db)):
    log_request("CDATA-GET", request)
    params = dict(request.query_params)
    sn = get_sn(request)
    options = params.get("options")

    # This is a handshake!
    if options and ("all" in options or "options" in options):
        if not sn:
            logger.error("  Handshake missing SN, rejecting")
            return PlainTextResponse("ERROR")

        device = get_device(db, sn)
        if not device:
            logger.error(f"  Device {sn} not found in database, rejecting")
            return PlainTextResponse("ERROR")

        logger.info("=" * 100)
        logger.info(f"  PERFORMING FULL HANDSHAKE FOR DEVICE {sn}")
        logger.info("=" * 100)

        # Update device's last seen & last sync
        device_service.update_last_seen(db, device.id)
        device_service.update_last_sync(db, device.id)

        # Exactly following msaied/zkteco-php Legacy + Push SDK config!
        config_lines = [
            f"GET OPTION FROM: {sn}",
            "Stamp=0",
            "OpStamp=0",
            "ErrorDelay=30",
            "Delay=10",
            "TransTimes=00:00;14:05",
            "TransInterval=1",
            "TransFlag=1111111111",
            "Realtime=1",  # KEY: enables real-time attendance upload!
            "Encrypt=0",
            # Push SDK additions for Ver 8.x firmware!
            "BioDataFun=1",
            "RtDataFun=1",
            "BioStamp=0",
            "RtStamp=0",
        ]

        # Join with CRLF as required by ZKTeco firmware
        response_content = "\r\n".join(config_lines) + "\r\n"

        logger.info(f"  SENDING EXACT CONFIG BLOCK:")
        for line in response_content.split("\n"):
            logger.info(f"    {repr(line)}")

        logger.info("=" * 100)
        logger.info("  HANDSHAKE COMPLETE!")
        logger.info("=" * 100)

        return PlainTextResponse(
            response_content,
            media_type="text/plain"
        )

    # If not an options handshake, just update last seen
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")


@router.post("/cdata")
async def handle_cdata_post(request: Request, db: Session = Depends(get_db)):
    log_request("CDATA-POST", request)
    logger.info("=" * 100)
    logger.info("  INCOMING DATA UPLOAD")
    logger.info("=" * 100)

    # Read everything
    try:
        form_data = await request.form()
        logger.info(f"  Form data: {dict(form_data)}")
        raw_body = await request.body()
        logger.info(f"  Raw body (first 500 chars): {raw_body.decode('utf-8', errors='replace')[:500]}")
    except Exception as e:
        logger.error(f"  Error parsing form data: {e}")
        raw_body = await request.body()
        logger.info(f"  Raw body: {raw_body}")
        form_data = {}

    # Get SN from params or form
    params = dict(request.query_params)
    sn = get_sn(request) or form_data.get("SN") or form_data.get("sn")

    if not sn:
        logger.error("  No SN found, rejecting")
        return PlainTextResponse("ERROR")

    device = get_device(db, sn)
    if not device:
        logger.error(f"  Device {sn} not found, rejecting")
        return PlainTextResponse("ERROR")

    # Update timestamps
    device_service.update_last_seen(db, device.id)
    device_service.update_last_sync(db, device.id)

    # Check what table is being uploaded
    table = params.get("table") or form_data.get("table")
    logger.info(f"  Uploading table: {table}")

    # Process ATTLOG or RTLOG
    if table and ("ATTLOG" in table.upper() or "RTLOG" in table.upper()):
        records_text = (
            params.get("records") or
            form_data.get("records") or
            raw_body.decode("utf-8", errors="replace")
        )

        logger.info(f"  Processing records: {records_text}")

        count = 0
        for line in records_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Split by tabs or commas
            parts = line.split("\t") if "\t" in line else line.split(",")
            if len(parts) < 2:
                logger.warning(f"  Skipping malformed line: {line}")
                continue

            pin = parts[0].strip()
            time_str = parts[1].strip()
            status = parts[2].strip() if len(parts) > 2 else "0"
            verify = parts[3].strip() if len(parts) > 3 else "1"

            try:
                try:
                    check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        check_time = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                    except ValueError:
                        logger.warning(f"  Could not parse time: {time_str}, skipping")
                        continue

                logger.info(f"  Creating attendance record for PIN {pin} at {check_time}")

                attendance_log_service.create(
                    db=db,
                    device=device,
                    employee_code=pin,
                    check_time=check_time,
                    attendance_type=str(status),
                    verify_type=str(verify),
                    raw_data={"raw_line": line},
                    record_id=f"{device.id}-{pin}-{time_str}"
                )

                count += 1
                logger.info(f"  Successfully saved record {count}")

            except Exception as e:
                logger.error(f"  Error processing record line {line}: {e}", exc_info=True)

        logger.info(f"  Done processing {count} attendance records")

    logger.info("=" * 100)

    return PlainTextResponse("OK")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_other_requests(request: Request, db: Session = Depends(get_db)):
    log_request(f"OTHER-{request.method}", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")
