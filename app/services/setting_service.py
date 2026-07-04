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

    def get_settings(self, db: Session) -> CompanySettingResponse:
        settings = db.query(CompanySetting).first()
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
        )

    def update_settings(self, db: Session, payload: CompanySettingUpdate) -> CompanySettingResponse:
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
        if (payload.workplace_latitude is None) ^ (payload.workplace_longitude is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يجب إدخال خط العرض وخط الطول معًا عند تحديد موقع المركز.",
            )
        if payload.check_in_close_time <= payload.check_in_open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="وقت إغلاق نافذة الحضور يجب أن يكون بعد وقت بدايتها.",
            )
        if payload.check_out_close_time <= payload.check_out_open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="وقت إغلاق نافذة الانصراف يجب أن يكون بعد وقت بدايتها.",
            )
        if payload.check_out_open_time <= payload.check_in_open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="نافذة الانصراف يجب أن تبدأ بعد بداية نافذة الحضور.",
            )

        normalized_ip_ranges = [self._validate_ip_rule(item) for item in payload.allowed_ip_ranges]
        if payload.enforce_geofence and (payload.workplace_latitude is None or payload.workplace_longitude is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يجب تحديد خط العرض وخط الطول قبل تفعيل التحقق من موقع المركز.",
            )
        if payload.enforce_ip_check and not payload.allowed_ip_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يجب إدخال نطاق IP واحد على الأقل قبل تفعيل التحقق من شبكة العمل.",
            )

        settings = db.query(CompanySetting).first()
        settings.company_name = payload.company_name
        settings.work_start_time = payload.work_start_time
        settings.work_end_time = payload.work_end_time
        settings.weekend_days = ",".join(payload.weekend_days)
        settings.late_grace_minutes = payload.late_grace_minutes
        settings.workplace_latitude = payload.workplace_latitude
        settings.workplace_longitude = payload.workplace_longitude
        settings.workplace_radius_meters = payload.workplace_radius_meters
        settings.allowed_ip_ranges = ",".join(normalized_ip_ranges)
        settings.enforce_geofence = payload.enforce_geofence
        settings.enforce_ip_check = payload.enforce_ip_check
        settings.face_match_threshold = payload.face_match_threshold
        settings.check_in_open_time = payload.check_in_open_time
        settings.check_in_close_time = payload.check_in_close_time
        settings.check_out_open_time = payload.check_out_open_time
        settings.check_out_close_time = payload.check_out_close_time
        settings.auto_backup_enabled = payload.auto_backup_enabled
        settings.auto_backup_time = payload.auto_backup_time
        settings.auto_backup_retention_days = payload.auto_backup_retention_days
        db.commit()
        db.refresh(settings)
        return self.get_settings(db)
