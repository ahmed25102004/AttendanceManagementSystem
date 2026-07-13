from datetime import time
from ipaddress import ip_address, ip_network

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company_setting import CompanySetting
from app.schemas.setting import CompanySettingResponse, CompanySettingUpdate


class SettingService:
    _VALID_WEEKEND_DAYS = {
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    }

    def _validate_ip_rule(self, rule: str) -> str:
        normalized_rule = rule.strip()
        if not normalized_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن حفظ نطاق IP فارغ ضمن إعدادات مكان العمل.",
            )
        try:
            if "/" in normalized_rule:
                ip_network(normalized_rule, strict=False)
            else:
                ip_address(normalized_rule)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"صيغة نطاق IP غير صالحة: {normalized_rule}",
            ) from exc
        return normalized_rule

    def get_settings(self, db: Session, branch_id: int | None = None) -> CompanySettingResponse:
        query = db.query(CompanySetting)
        if branch_id:
            settings = query.filter(CompanySetting.branch_id == branch_id).first()
            if not settings:
                # If no settings for this branch, create default ones
                global_settings = db.query(CompanySetting).filter(CompanySetting.branch_id.is_(None)).first()
                settings = CompanySetting(
                    branch_id=branch_id,
                    company_name=global_settings.company_name if global_settings else "شركة",
                    work_start_time=global_settings.work_start_time if global_settings else time(9, 0),
                    work_end_time=global_settings.work_end_time if global_settings else time(17, 0),
                    weekend_days=global_settings.weekend_days if global_settings else "Saturday,Sunday",
                    late_grace_minutes=global_settings.late_grace_minutes if global_settings else 15,
                    workplace_latitude=global_settings.workplace_latitude if global_settings else None,
                    workplace_longitude=global_settings.workplace_longitude if global_settings else None,
                    workplace_radius_meters=global_settings.workplace_radius_meters if global_settings else 150,
                    allowed_ip_ranges=global_settings.allowed_ip_ranges if global_settings else "",
                    enforce_geofence=global_settings.enforce_geofence if global_settings else False,
                    enforce_ip_check=global_settings.enforce_ip_check if global_settings else False,
                    face_match_threshold=global_settings.face_match_threshold if global_settings else 0.6,
                    check_in_open_time=global_settings.check_in_open_time if global_settings else time(8, 0),
                    check_in_close_time=global_settings.check_in_close_time if global_settings else time(11, 0),
                    check_out_open_time=global_settings.check_out_open_time if global_settings else time(16, 0),
                    check_out_close_time=global_settings.check_out_close_time if global_settings else time(22, 0),
                    auto_backup_enabled=global_settings.auto_backup_enabled if global_settings else False,
                    auto_backup_time=global_settings.auto_backup_time if global_settings else time(2, 0),
                    auto_backup_retention_days=global_settings.auto_backup_retention_days if global_settings else 30,
                    zkteco_enabled=global_settings.zkteco_enabled if hasattr(global_settings, 'zkteco_enabled') else False,
                    zkteco_ip=global_settings.zkteco_ip if hasattr(global_settings, 'zkteco_ip') else "192.168.1.201",
                    zkteco_port=global_settings.zkteco_port if hasattr(global_settings, 'zkteco_port') else 4370,
                    zkteco_password=global_settings.zkteco_password if hasattr(global_settings, 'zkteco_password') else "",
                    zkteco_auto_sync_enabled=global_settings.zkteco_auto_sync_enabled if hasattr(global_settings, 'zkteco_auto_sync_enabled') else False,
                    zkteco_auto_sync_interval_minutes=global_settings.zkteco_auto_sync_interval_minutes if hasattr(global_settings, 'zkteco_auto_sync_interval_minutes') else 30,
                )
                db.add(settings)
                db.commit()
                db.refresh(settings)
        else:
            settings = query.filter(CompanySetting.branch_id.is_(None)).first()
            if not settings:
                # If no global settings, create default ones
                settings = CompanySetting(
                    company_name="شركة",
                )
                db.add(settings)
                db.commit()
                db.refresh(settings)
        return CompanySettingResponse(
            id=settings.id,
            company_name=settings.company_name,
            work_start_time=settings.work_start_time,
            work_end_time=settings.work_end_time,
            weekend_days=[day.strip() for day in settings.weekend_days.split(",") if day.strip()],
            late_grace_minutes=settings.late_grace_minutes,
            workplace_latitude=settings.workplace_latitude,
            workplace_longitude=settings.workplace_longitude,
            workplace_radius_meters=settings.workplace_radius_meters,
            allowed_ip_ranges=[item.strip() for item in settings.allowed_ip_ranges.split(",") if item.strip()],
            enforce_geofence=settings.enforce_geofence,
            enforce_ip_check=settings.enforce_ip_check,
            face_match_threshold=settings.face_match_threshold,
            check_in_open_time=settings.check_in_open_time,
            check_in_close_time=settings.check_in_close_time,
            check_out_open_time=settings.check_out_open_time,
            check_out_close_time=settings.check_out_close_time,
            auto_backup_enabled=settings.auto_backup_enabled,
            auto_backup_time=settings.auto_backup_time,
            auto_backup_retention_days=settings.auto_backup_retention_days,
            zkteco_enabled=settings.zkteco_enabled if hasattr(settings, 'zkteco_enabled') else False,
            zkteco_ip=settings.zkteco_ip if hasattr(settings, 'zkteco_ip') else "192.168.1.201",
            zkteco_port=settings.zkteco_port if hasattr(settings, 'zkteco_port') else 4370,
            zkteco_password=settings.zkteco_password if hasattr(settings, 'zkteco_password') else "",
            zkteco_auto_sync_enabled=settings.zkteco_auto_sync_enabled if hasattr(settings, 'zkteco_auto_sync_enabled') else False,
            zkteco_auto_sync_interval_minutes=settings.zkteco_auto_sync_interval_minutes if hasattr(settings, 'zkteco_auto_sync_interval_minutes') else 30,
        )

    def update_settings(self, db: Session, payload: CompanySettingUpdate, branch_id: int | None = None) -> CompanySettingResponse:
        if payload.work_end_time <= payload.work_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="وقت نهاية العمل يجب أن يكون بعد وقت بداية العمل.",
            )
        if len(set(payload.weekend_days)) != len(payload.weekend_days):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن تكرار نفس يوم العطلة الأسبوعية أكثر من مرة.",
            )
        invalid_days = [day for day in payload.weekend_days if day not in self._VALID_WEEKEND_DAYS]
        if invalid_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="تتضمن أيام العطلة الأسبوعية قيمة غير مدعومة.",
            )

        if branch_id:
            settings = db.query(CompanySetting).filter(CompanySetting.branch_id == branch_id).first()
            if not settings:
                # Create settings for this branch
                settings = CompanySetting(branch_id=branch_id)
                db.add(settings)
        else:
            settings = db.query(CompanySetting).filter(CompanySetting.branch_id.is_(None)).first()
            if not settings:
                settings = CompanySetting()
                db.add(settings)

        settings.company_name = payload.company_name
        settings.work_start_time = payload.work_start_time
        settings.work_end_time = payload.work_end_time
        settings.weekend_days = ",".join(payload.weekend_days)
        settings.late_grace_minutes = payload.late_grace_minutes
        settings.auto_backup_enabled = payload.auto_backup_enabled
        settings.auto_backup_time = payload.auto_backup_time
        settings.auto_backup_retention_days = payload.auto_backup_retention_days
        
        # Add ZKTeco settings
        settings.zkteco_enabled = payload.zkteco_enabled
        settings.zkteco_ip = payload.zkteco_ip or ""
        settings.zkteco_port = payload.zkteco_port
        settings.zkteco_password = payload.zkteco_password or ""
        settings.zkteco_auto_sync_enabled = payload.zkteco_auto_sync_enabled
        settings.zkteco_auto_sync_interval_minutes = payload.zkteco_auto_sync_interval_minutes
        
        db.commit()
        db.refresh(settings)
        return self.get_settings(db, branch_id)
