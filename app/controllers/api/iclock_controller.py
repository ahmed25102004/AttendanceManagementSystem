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
logger.setLevel(logging.DEBUG)


def log_request(prefix: str, request: Request):
    logger.info(f"[{prefix}] {request.method} {request.url}")
    logger.info(f"Params: {dict(request.query_params)}")


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
    log_request("GETREQUEST", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
            logger.info(f"GETREQUEST: Device {sn} connected")
    return PlainTextResponse("")


@router.get("/getinfo")
async def handle_getinfo(request: Request, db: Session = Depends(get_db)):
    log_request("GETINFO", request)
    return PlainTextResponse("Ret=0")


@router.get("/gettime")
async def handle_gettime(request: Request, db: Session = Depends(get_db)):
    log_request("GETTIME", request)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return PlainTextResponse(f"Ret=0\nTime={now}")


@router.get("/ping")
async def handle_ping(request: Request, db: Session = Depends(get_db)):
    log_request("PING", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")


@router.get("/cdata")
async def handle_cdata_get(request: Request, db: Session = Depends(get_db)):
    log_request("CDATA-GET", request)
    params = dict(request.query_params)
    sn = get_sn(request)
    options = params.get("options")

    logger.info("="*100)
    logger.info(f"OPTIONS PARAMS: {params}")
    logger.info("="*100)

    if options and "all" in options:
        if not sn:
            logger.warning("Handshake missing SN")
            return PlainTextResponse("ERROR")
        device = get_device(db, sn)
        if not device:
            logger.error(f"Unknown device {sn}")
            return PlainTextResponse("ERROR")

        device_service.update_last_seen(db, device.id)

        res_lines = [
            f"GET OPTION FROM: {sn}",
            "ATTLOGStamp=0",
            "OPERLOGStamp=0",
            "ErrorDelay=10",
            "Delay=5",
            "TransTimes=00:00;23:59",
            "TransInterval=1",
            "Realtime=1",
            "ServerVer=3.0.1",
            "PushProtVer=2.4.1",
            "TimeZone=0"
        ]
        res = "\r\n".join(res_lines)
        logger.info("="*100)
        logger.info("RESPONDING WITH HANDSHAKE:")
        logger.info(repr(res))
        logger.info("="*100)
        return PlainTextResponse(res, media_type="text/plain")
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")


@router.post("/cdata")
async def handle_cdata_post(request: Request, db: Session = Depends(get_db)):
    log_request("CDATA-POST", request)
    logger.info("="*100)
    try:
        form_data = await request.form()
        logger.info(f"FORM: {dict(form_data)}")
        raw = await request.body()
        logger.info(f"BODY: {raw}")
    except Exception as e:
        logger.error(e)
        raw = await request.body()
        logger.info(f"RAW BODY: {raw}")
        form_data = {}
    params = dict(request.query_params)
    sn = get_sn(request) or form_data.get("SN") or form_data.get("sn")

    if not sn:
        return PlainTextResponse("ERROR")

    device = get_device(db, sn)
    if not device:
        return PlainTextResponse("ERROR")
    device_service.update_last_seen(db, device.id)

    table = params.get("table") or form_data.get("table")
    logger.info(f"TABLE: {table}")

    if table and "ATTLOG" in table.upper():
        records = params.get("records") or form_data.get("records") or ""
        logger.info(f"RECORDS: {records}")
        for line in records.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t") if "\t" in line else line.split(",")
            if len(parts) < 2:
                continue
            pin = parts[0].strip()
            t_str = parts[1].strip()
            try:
                check_time = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.error(e)
                try:
                    check_time = datetime.strptime(t_str, "%Y/%m/%d %H:%M:%S")
                except:
                    continue

            attendance_log_service.create(
                db=db,
                device=device,
                employee_code=pin,
                check_time=check_time,
                attendance_type="0",
                verify_type="1",
                raw_data=dict(raw_line=line),
                record_id=f"{device.id}-{pin}-{t_str}"
            )
            logger.info(f"LOG CREATED")
    return PlainTextResponse("OK")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def handle_other(request: Request, db: Session = Depends(get_db)):
    log_request(f"OTHER_{request.method}", request)
    sn = get_sn(request)
    if sn:
        device = get_device(db, sn)
        if device:
            device_service.update_last_seen(db, device.id)
    return PlainTextResponse("OK")
