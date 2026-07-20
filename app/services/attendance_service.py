from datetime import date, datetime
from ipaddress import ip_address, ip_network
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from starlette.requests import Request

from app.models.attendance import AttendanceRecord
from app.models.company_setting import CompanySetting
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceManualUpdate,
    AttendanceResponse,
    FaceAttendanceRequest,
    FacePortalStatusResponse,
    FaceRegistrationRequest,
    FaceRegistrationResponse,
    FaceScanResponse,
    SelfAttendanceRequest,
)
from app.services.biometric_service import FaceRecognitionMatcher, VerificationProviderFactory
from app.services.attendance_policies import AttendancePolicyFactory


class AttendanceService:
    def __init__(self) -> None:
        self.provider_factory = VerificationProviderFactory()
        self.face_matcher = FaceRecognitionMatcher()
        self.policy_factory = AttendancePolicyFactory()

    def _calculate_late_status(self, db: Session, employee: Employee, check_in_time: datetime) -> bool:
        policy = self.policy_factory.get_policy_for_employee(db, employee)
        return policy.calculate_late_status(db, employee, check_in_time)

    def _calculate_late_minutes(self, db: Session, employee: Employee, check_in_time: datetime) -> int:
        policy = self.policy_factory.get_policy_for_employee(db, employee)
        return policy.calculate_late_minutes(db, employee, check_in_time)

    def _is_doctors_department(self, employee: Employee) -> bool:
        return bool(employee.department and employee.department.attendance_policy == "doctors_department")
    
    def _is_leather_department(self, employee: Employee) -> bool:
        return bool(employee.department and employee.department.attendance_policy == "leather_department")

    def _apply_shift_metrics(self, employee: Employee, record: AttendanceRecord) -> None:
        record.shift_category = None
        record.shift_units = 0.0
        
        # Leather department: no shift metrics
        if self._is_leather_department(employee):
            return

        if not self._is_doctors_department(employee) or not record.check_in_time or not record.check_out_time:
            return
        
        # Use doctors department policy to get shift type
        policy = self.policy_factory.get_policy_for_employee(None, employee)
        if hasattr(policy, 'get_shift_type'):
            raw_shift_type = policy.get_shift_type(employee, record.check_in_time, record.check_out_time)
            shift_type_map = {
                "شفت كامل": "full_shift",
                "نصف شيفت": "half_shift",
                "نقص في الشفت": "incomplete",
            }
            shift_type = shift_type_map.get(raw_shift_type, raw_shift_type)
            record.shift_category = shift_type

            if shift_type == "full_shift":
                record.shift_units = 1.0  # Full shift is one unit
            elif shift_type == "half_shift":
                record.shift_units = 0.5  # Half shift is 0.5 units
            else:
                record.shift_units = 0.0

    def _to_response(self, record: AttendanceRecord) -> AttendanceResponse:
        employee_name = " ".join(
            part.strip() for part in [record.employee.first_name, record.employee.last_name] if part and part.strip()
        )
        return AttendanceResponse(
            id=record.id,
            employee_id=record.employee_id,
            employee_name=employee_name,
            attendance_date=record.attendance_date,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            working_hours=round(record.working_hours, 2),
            shift_category=record.shift_category,
            shift_units=record.shift_units,
            overtime_hours=getattr(record, 'overtime_hours', 0.0),
            shift_deficit_hours=getattr(record, 'shift_deficit_hours', 0.0),
            is_late=record.is_late,
            late_minutes=record.late_minutes,
            status=record.status,
            source_type=record.source_type,
            is_rest_day=record.is_rest_day,
            worked_on_rest_day=record.worked_on_rest_day,
        )

    def _get_company_settings(self, db: Session) -> CompanySetting:
        settings = db.query(CompanySetting).first()
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="إعدادات المركز غير مكتملة. يرجى مراجعة الإعدادات أولًا.",
            )
        return settings

    def _get_employee(self, db: Session, employee_id: int) -> Employee:
        employee = db.query(Employee).options(joinedload(Employee.department)).filter(Employee.id == employee_id, Employee.is_active.is_(True)).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموظف غير موجود.")
        return employee

    def _get_employee_for_user(self, db: Session, current_user: User) -> Employee:
        if not current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="المستخدم الحالي غير مرتبط بملف موظف.")
        return self._get_employee(db, current_user.employee_id)

    def _resolve_client_ip(self, request: Request) -> str | None:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return None

    def _ip_matches_rule(self, client_ip: str, rule: str) -> bool:
        normalized_rule = rule.strip()
        if not normalized_rule:
            return False
        try:
            if "/" in normalized_rule:
                return ip_address(client_ip) in ip_network(normalized_rule, strict=False)
            return ip_address(client_ip) == ip_address(normalized_rule)
        except ValueError:
            return client_ip.startswith(normalized_rule)

    def _distance_meters(self, latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> float:
        radius = 6371000
        lat_1, lon_1, lat_2, lon_2 = map(radians, [latitude_1, longitude_1, latitude_2, longitude_2])
        delta_lat = lat_2 - lat_1
        delta_lon = lon_2 - lon_1
        haversine = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        return 2 * radius * asin(sqrt(haversine))

    def _validate_workplace_access(
        self,
        db: Session,
        request: Request,
        payload: SelfAttendanceRequest | FaceAttendanceRequest,
    ) -> dict:
        settings = self._get_company_settings(db)
        verification_context: dict[str, object] = {
            "access_method": "self_service",
            "ip_verified": False,
            "location_verified": False,
            "request_ip": self._resolve_client_ip(request),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "accuracy_meters": payload.accuracy_meters,
        }

        if settings.enforce_ip_check:
            allowed_rules = [item.strip() for item in settings.allowed_ip_ranges.split(",") if item.strip()]
            if not allowed_rules:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="يجب على المدير إعداد نطاقات IP الخاصة بالعمل قبل تفعيل التسجيل الذاتي.",
                )
            request_ip = verification_context["request_ip"]
            if not request_ip or not any(self._ip_matches_rule(str(request_ip), rule) for rule in allowed_rules):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="التسجيل الذاتي مسموح فقط من شبكة العمل المعتمدة.",
                )
            verification_context["ip_verified"] = True

        if settings.enforce_geofence:
            if settings.workplace_latitude is None or settings.workplace_longitude is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="يجب على المدير تحديد موقع العمل قبل تفعيل التحقق الجغرافي.",
                )
            if payload.latitude is None or payload.longitude is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="يجب السماح بمشاركة الموقع لتسجيل الحضور أو الانصراف.",
                )

            distance = self._distance_meters(
                payload.latitude,
                payload.longitude,
                settings.workplace_latitude,
                settings.workplace_longitude,
            )
            verification_context["distance_meters"] = round(distance, 2)
            if distance > settings.workplace_radius_meters:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="التسجيل الذاتي متاح فقط من داخل نطاق مكان العمل.",
                )
            verification_context["location_verified"] = True

        return verification_context

    def _get_record_for_employee_date(
        self,
        db: Session,
        employee_id: int,
        attendance_date: date,
        with_employee: bool = False,
    ) -> AttendanceRecord | None:
        query = db.query(AttendanceRecord)
        if with_employee:
            query = query.options(joinedload(AttendanceRecord.employee))
        return query.filter(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.attendance_date == attendance_date,
        ).first()

    def _within_window(self, current_time_value, start_time, end_time) -> bool:
        return start_time <= current_time_value <= end_time

    def _get_face_confidence(self, distance: float, threshold: float) -> float:
        scale = max(threshold * 2, 0.0001)
        return round(max(0.0, min(1.0, 1 - (distance / scale))), 4)

    def _merge_record_verification(self, db: Session, record_id: int, payload: dict) -> None:
        record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
        if not record:
            return
        record.verification_data = {**(record.verification_data or {}), **payload}
        db.commit()

    def _resolve_face_scan_action(
        self,
        settings: CompanySetting,
        record: AttendanceRecord | None,
        current_timestamp: datetime,
    ) -> tuple[str, str]:
        current_time_value = current_timestamp.time()
        within_check_in = self._within_window(current_time_value, settings.check_in_open_time, settings.check_in_close_time)
        within_check_out = self._within_window(current_time_value, settings.check_out_open_time, settings.check_out_close_time)

        if record and record.check_out_time:
            return "already_completed", "تم تسجيل حضورك وانصرافك مسبقًا لهذا اليوم."
        if (not record or not record.check_in_time) and within_check_in:
            return "check_in", "تم التعرف على الوجه داخل نافذة الحضور، وسيتم تسجيل الحضور تلقائيًا."
        if record and record.check_in_time and not record.check_out_time and within_check_out:
            return "check_out", "تم التعرف على الوجه داخل نافذة الانصراف، وسيتم تسجيل الانصراف تلقائيًا."
        if record and record.check_in_time and not record.check_out_time:
            return "already_checked_in", "تم تسجيل حضورك مسبقًا. انتظر نافذة الانصراف ليتم تسجيله تلقائيًا."
        if within_check_out:
            return "wait", "لا يمكن تسجيل الانصراف قبل وجود حضور مسجل لهذا اليوم."
        return "wait", "خارج نافذة الحضور والانصراف التلقائي حاليًا."

    def get_face_portal_status(self, db: Session, current_user: User) -> FacePortalStatusResponse:
        employee = self._get_employee_for_user(db, current_user)
        settings = self._get_company_settings(db)
        return FacePortalStatusResponse(
            face_registered=bool(employee.face_descriptor),
            face_registered_at=employee.face_registered_at,
            face_verification_enabled=employee.face_verification_enabled,
            face_match_threshold=settings.face_match_threshold,
            check_in_open_time=settings.check_in_open_time,
            check_in_close_time=settings.check_in_close_time,
            check_out_open_time=settings.check_out_open_time,
            check_out_close_time=settings.check_out_close_time,
        )

    def register_face(self, db: Session, current_user: User, payload: FaceRegistrationRequest) -> FaceRegistrationResponse:
        employee = self._get_employee_for_user(db, current_user)
        if not employee.face_verification_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="تسجيل الوجه معطل لهذا الموظف. يرجى مراجعة الإدارة.",
            )

        try:
            averaged_descriptor = self.face_matcher.average_descriptors(payload.descriptors)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        employee.face_descriptor = averaged_descriptor
        employee.face_registered_at = datetime.now()
        db.commit()
        db.refresh(employee)
        return FaceRegistrationResponse(
            face_registered=True,
            face_registered_at=employee.face_registered_at,
            sample_count=len(payload.descriptors),
        )

    def process_face_scan(
        self,
        db: Session,
        current_user: User,
        request: Request,
        payload: FaceAttendanceRequest,
    ) -> FaceScanResponse:
        employee = self._get_employee_for_user(db, current_user)
        settings = self._get_company_settings(db)
        if not employee.face_verification_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="التحقق بالوجه معطل لهذا الموظف.",
            )
        if not employee.face_descriptor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لم يتم تسجيل بصمة الوجه لهذا الموظف بعد.",
            )

        verification_context = self._validate_workplace_access(db, request, payload)
        try:
            distance = self.face_matcher.distance(employee.face_descriptor, payload.descriptor)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        confidence = self._get_face_confidence(distance, settings.face_match_threshold)
        attendance_date = payload.attendance_date or date.today()
        current_record = self._get_record_for_employee_date(db, employee.id, attendance_date, with_employee=True)
        if distance > settings.face_match_threshold:
            return FaceScanResponse(
                matched=False,
                action="mismatch",
                message="تعذر مطابقة الوجه الحالي مع الحساب المسجل.",
                confidence=confidence,
                distance=round(distance, 4),
                record=self._to_response(current_record) if current_record else None,
            )

        current_timestamp = datetime.now()
        verification_context.update(
            {
                "provider": "face_auto",
                "face_verified": True,
                "face_distance": round(distance, 4),
                "face_confidence": confidence,
            }
        )
        action, message = self._resolve_face_scan_action(settings, current_record, current_timestamp)

        if action == "check_in":
            record = self.check_in(
                db,
                AttendanceCheckIn(
                    employee_id=employee.id,
                    attendance_date=attendance_date,
                    check_in_time=current_timestamp,
                    source_type="face",
                    verification_data=verification_context,
                ),
            )
            return FaceScanResponse(
                matched=True,
                action=action,
                message="تم تسجيل الحضور تلقائيًا بعد التعرف على الوجه.",
                confidence=confidence,
                distance=round(distance, 4),
                record=record,
            )

        if action == "check_out":
            record = self.check_out(
                db,
                AttendanceCheckOut(
                    employee_id=employee.id,
                    attendance_date=attendance_date,
                    check_out_time=current_timestamp,
                ),
            )
            self._merge_record_verification(db, record.id, verification_context)
            refreshed_record = self._get_record_for_employee_date(db, employee.id, attendance_date, with_employee=True)
            return FaceScanResponse(
                matched=True,
                action=action,
                message="تم تسجيل الانصراف تلقائيًا بعد التعرف على الوجه.",
                confidence=confidence,
                distance=round(distance, 4),
                record=self._to_response(refreshed_record) if refreshed_record else record,
            )

        return FaceScanResponse(
            matched=True,
            action=action,
            message=message,
            confidence=confidence,
            distance=round(distance, 4),
            record=self._to_response(current_record) if current_record else None,
        )

    def check_in(self, db: Session, payload: AttendanceCheckIn) -> AttendanceResponse:
        employee = self._get_employee(db, payload.employee_id)
        attendance_date = payload.attendance_date or date.today()
        check_in_time = payload.check_in_time or datetime.now()

        existing = self._get_record_for_employee_date(db, payload.employee_id, attendance_date)
        if existing and existing.check_in_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تم تسجيل حضور الموظف بالفعل في هذا التاريخ.")

        provider = self.provider_factory.create(payload.source_type)
        try:
            verification = provider.verify(payload.verification_data)
        except (NotImplementedError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        record = existing or AttendanceRecord(
            employee_id=payload.employee_id,
            attendance_date=attendance_date,
        )
        record.check_in_time = check_in_time
        record.source_type = payload.source_type
        record.verification_data = verification
        record.is_rest_day = self.policy_factory.get_policy_for_employee(db, employee).is_rest_day(db, employee, attendance_date)
        record.worked_on_rest_day = record.is_rest_day
        record.late_minutes = self._calculate_late_minutes(db, employee, check_in_time)
        record.is_late = record.late_minutes > 0
        record.shift_category = None
        record.shift_units = 0.0
        record.status = "present"

        db.add(record)
        db.commit()
        db.refresh(record)
        record = (
            db.query(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .filter(AttendanceRecord.id == record.id)
            .first()
        )
        return self._to_response(record)

    def check_out(self, db: Session, payload: AttendanceCheckOut) -> AttendanceResponse:
        employee = self._get_employee(db, payload.employee_id)
        attendance_date = payload.attendance_date or date.today()
        check_out_time = payload.check_out_time or datetime.now()
        record = self._get_record_for_employee_date(db, payload.employee_id, attendance_date)

        if not record or not record.check_in_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لم يتم تسجيل حضور الموظف في هذا التاريخ.")
        if record.check_out_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تم تسجيل انصراف الموظف بالفعل في هذا التاريخ.")
        if check_out_time < record.check_in_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن أن يكون وقت الانصراف قبل وقت الحضور.")

        record.check_out_time = check_out_time
        policy = self.policy_factory.get_policy_for_employee(db, employee)
        record.working_hours = policy.calculate_working_hours(record.check_in_time, record.check_out_time)
        
        # Calculate overtime and shift deficit for departments that support it
        if hasattr(policy, 'calculate_overtime_hours') and hasattr(policy, 'calculate_shift_deficit_hours'):
            record.overtime_hours = policy.calculate_overtime_hours(employee, record.check_in_time, record.check_out_time)
            record.shift_deficit_hours = policy.calculate_shift_deficit_hours(employee, record.check_in_time, record.check_out_time)
        else:
            record.overtime_hours = 0.0
            record.shift_deficit_hours = 0.0
            
        self._apply_shift_metrics(employee, record)
        record.worked_on_rest_day = bool(record.is_rest_day and record.check_in_time)
        db.commit()
        db.refresh(record)
        record = (
            db.query(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .filter(AttendanceRecord.id == record.id)
            .first()
        )
        return self._to_response(record)

    def self_check_in(self, db: Session, current_user: User, request: Request, payload: SelfAttendanceRequest) -> AttendanceResponse:
        employee = self._get_employee_for_user(db, current_user)
        
        # Validate workplace access (geofence and IP)
        verification_context = self._validate_workplace_access(db, request, payload)
        
        # Call check_in with appropriate payload
        return self.check_in(
            db,
            AttendanceCheckIn(
                employee_id=employee.id,
                attendance_date=date.today(),
                check_in_time=datetime.now(),
                source_type="self_service",
                verification_data=verification_context
            )
        )

    def self_check_out(self, db: Session, current_user: User, request: Request, payload: SelfAttendanceRequest) -> AttendanceResponse:
        employee = self._get_employee_for_user(db, current_user)
        
        # Validate workplace access (geofence and IP)
        verification_context = self._validate_workplace_access(db, request, payload)
        
        # Call check_out with appropriate payload
        return self.check_out(
            db,
            AttendanceCheckOut(
                employee_id=employee.id,
                attendance_date=date.today(),
                check_out_time=datetime.now(),
                verification_data=verification_context
            )
        )

    def upsert_manual_record(self, db: Session, payload: AttendanceManualUpdate) -> AttendanceResponse:
        employee = self._get_employee(db, payload.employee_id)
        record = self._get_record_for_employee_date(db, payload.employee_id, payload.attendance_date)
        policy = self.policy_factory.get_policy_for_employee(db, employee)

        if record is None:
            record = AttendanceRecord(
                employee_id=payload.employee_id,
                attendance_date=payload.attendance_date,
            )

        record.check_in_time = payload.check_in_time
        record.check_out_time = payload.check_out_time
        record.source_type = payload.source_type
        record.is_rest_day = policy.is_rest_day(db, employee, payload.attendance_date)
        record.worked_on_rest_day = bool(record.is_rest_day and record.check_in_time)

        if record.check_in_time:
            record.late_minutes = policy.calculate_late_minutes(db, employee, record.check_in_time)
            record.is_late = record.late_minutes > 0
        else:
            record.late_minutes = 0
            record.is_late = False

        if record.check_in_time and record.check_out_time:
            if record.check_out_time < record.check_in_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="لا يمكن أن يكون وقت الانصراف قبل وقت الحضور.",
                )
            record.working_hours = policy.calculate_working_hours(record.check_in_time, record.check_out_time)
            
            # Calculate overtime and shift deficit for departments that support it
            if hasattr(policy, 'calculate_overtime_hours') and hasattr(policy, 'calculate_shift_deficit_hours'):
                record.overtime_hours = policy.calculate_overtime_hours(employee, record.check_in_time, record.check_out_time)
                record.shift_deficit_hours = policy.calculate_shift_deficit_hours(employee, record.check_in_time, record.check_out_time)
            else:
                record.overtime_hours = 0.0
                record.shift_deficit_hours = 0.0
                
            self._apply_shift_metrics(employee, record)
        else:
            record.working_hours = 0.0
            record.overtime_hours = 0.0
            record.shift_deficit_hours = 0.0
            record.shift_category = None
            record.shift_units = 0.0

        if record.check_in_time:
            record.status = "present_on_rest_day" if record.worked_on_rest_day else "present"
        elif record.is_rest_day:
            record.status = "weekly_rest"
        else:
            record.status = "absent"

        if payload.notes:
            record.verification_data = {**(record.verification_data or {}), "manual_notes": payload.notes}

        db.add(record)
        db.commit()
        db.refresh(record)
        record = (
            db.query(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .filter(AttendanceRecord.id == record.id)
            .first()
        )
        return self._to_response(record)

    def get_today_record_for_user(self, db: Session, current_user: User) -> AttendanceResponse | None:
        if not current_user.employee_id:
            return None
        record = self._get_record_for_employee_date(db, current_user.employee_id, date.today(), with_employee=True)
        if not record:
            return None
        return self._to_response(record)

    def list_records(self, db: Session, attendance_date: date | None = None, branch_id: int | None = None) -> list[AttendanceResponse]:
        query = db.query(AttendanceRecord).options(joinedload(AttendanceRecord.employee))
        if branch_id:
            query = query.join(Employee).filter(Employee.branch_id == branch_id)
        if attendance_date:
            query = query.filter(AttendanceRecord.attendance_date == attendance_date)
        records = query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id.desc()).all()
        return [self._to_response(record) for record in records]
