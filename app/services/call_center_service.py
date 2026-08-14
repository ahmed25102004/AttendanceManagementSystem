from __future__ import annotations
from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session, joinedload
from app.models.attendance import AttendanceRecord
from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.schemas.report import ReportRow


class CallCenterService:
    """Shared service for Call Center and Workers departments.

    Key rules:
    - Shift auto-detected from first check-in time.
      first < shift2_start  -> Shift 1 (morning)
      first >= shift2_start -> Shift 2 (evening)
    - Late = minutes AFTER grace-period end (not from shift start).
    - Deficit = early departure before shift end.
    - Overtime = staying after shift end.
    - Working on rest day: status='present', worked_on_rest_day=True.
    - Monthly summary: ONE row per employee (aggregated).
    - Detailed view: ONE row per day.
    """

    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def _fmt_time(self, v):
        return v.strftime("%H:%M") if v else None

    def _fmt_dt(self, v):
        return v.isoformat() if v else None

    def _full_name(self, emp):
        return " ".join(p.strip() for p in [emp.first_name, emp.last_name] if p and p.strip())

    def _day_name(self, d):
        return self.DAY_NAMES[d.weekday()]

    def _is_rest(self, emp, d):
        return bool(emp.weekly_rest_day and emp.weekly_rest_day.strip().lower() == self._day_name(d))

    def _shift_info(self, emp, first_log=None):
        dept = emp.department
        if not dept:
            return None
        s1 = {
            "label": "الشيفت الاول",
            "shift_type": "morning",
            "shift_category": "shift_1",
            "start_time": dept.shift_start_time,
            "late_time": dept.late_start_time,
            "end_time": dept.shift_end_time,
        }
        if not first_log or not dept.evening_shift_start_time:
            return s1
        if first_log.time() >= dept.evening_shift_start_time:
            return {
                "label": "الشيفت الثاني",
                "shift_type": "evening",
                "shift_category": "shift_2",
                "start_time": dept.evening_shift_start_time,
                "late_time": dept.evening_shift_late_start_time,
                "end_time": dept.evening_shift_end_time,
            }
        return s1

    def _late_min(self, si, cin):
        if not si or not cin or not si.get("late_time"):
            return 0
        t = datetime.combine(cin.date(), si["late_time"])
        return int((cin - t).total_seconds() // 60) if cin > t else 0

    def _deficit_h(self, si, cout):
        if not si or not cout or not si.get("end_time"):
            return 0.0
        e = datetime.combine(cout.date(), si["end_time"])
        return round((e - cout).total_seconds() / 3600, 2) if cout < e else 0.0

    def _ot_h(self, si, cout):
        if not si or not cout or not si.get("end_time"):
            return 0.0
        e = datetime.combine(cout.date(), si["end_time"])
        return round((cout - e).total_seconds() / 3600, 2) if cout > e else 0.0

    def _wh(self, f, l):
        if not f or not l or l <= f:
            return 0.0
        return round((l - f).total_seconds() / 3600, 2)

    def _iter_dates(self, s, e):
        cur = s
        while cur <= e:
            yield cur
            cur += timedelta(days=1)

    def _build_log_map(self, db, ids, sd, ed):
        if not ids:
            return {}
        logs = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.employee_id.in_(ids),
                AttendanceLog.check_time >= datetime.combine(sd, time.min),
                AttendanceLog.check_time < datetime.combine(ed + timedelta(days=1), time.min),
            )
            .order_by(AttendanceLog.check_time)
            .all()
        )
        g = {}
        for lg in logs:
            if not lg.employee_id:
                continue
            k = (lg.employee_id, lg.check_time.date())
            if k not in g:
                g[k] = {"first": lg.check_time, "last": lg.check_time}
            else:
                if lg.check_time < g[k]["first"]:
                    g[k]["first"] = lg.check_time
                if lg.check_time > g[k]["last"]:
                    g[k]["last"] = lg.check_time
        return g

    def _build_record_map(self, db, ids, sd, ed):
        if not ids:
            return {}
        return {
            (r.employee_id, r.attendance_date): r
            for r in db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id.in_(ids),
                AttendanceRecord.attendance_date >= sd,
                AttendanceRecord.attendance_date <= ed,
            )
            .all()
        }

    def _query_employees(self, db, dept_id, branch_id=None):
        return (
            db.query(Employee)
            .options(joinedload(Employee.department))
            .filter(Employee.department_id == dept_id, Employee.is_active.is_(True))
            .order_by(Employee.first_name.asc(), Employee.id.asc())
            .all()
        )

    def _day_metrics(self, emp, cur_date, rec, dlogs):
        is_rest = self._is_rest(emp, cur_date)
        if rec:
            fl, ll = rec.check_in_time, rec.check_out_time
        else:
            fl = dlogs["first"] if dlogs else None
            ll = dlogs["last"] if dlogs else None
            if fl and ll and ll <= fl:
                ll = None
        si = self._shift_info(emp, fl)
        wor = bool(fl and is_rest)
        is_manual = rec and getattr(rec, "is_manual_attendance", False)
        if is_manual and rec.working_hours is not None:
            wh = round(rec.working_hours, 2)
            lm = rec.late_minutes or 0
            dh = ot = 0.0
            st = rec.status or "present"
        else:
            lm = self._late_min(si, fl)
            wh = self._wh(fl, ll)
            dh = self._deficit_h(si, ll)
            ot = self._ot_h(si, ll)
            st = "present" if fl else ("weekly_rest" if is_rest else "absent")
        return {
            "current_date": cur_date,
            "shift_info": si,
            "first_log": fl,
            "last_log": ll,
            "working_hours": wh,
            "late_minutes": lm,
            "shift_deficit_hours": dh,
            "overtime_hours": ot,
            "status": st,
            "is_rest_day": is_rest,
            "worked_on_rest_day": wor,
        }

    def _make_daily_row(self, emp, m, absent, weekly_rest, rest_work):
        si = m["shift_info"]
        return ReportRow(
            row_kind="daily",
            employee_code=emp.employee_code,
            employee_name=self._full_name(emp),
            department=emp.department.name if emp.department else None,
            job_title=emp.job_title,
            attendance_date=m["current_date"].isoformat(),
            shift_name=si["label"] if si else None,
            shift_type=si["shift_type"] if si else None,
            shift_start_time=self._fmt_time(si["start_time"]) if si else None,
            shift_end_time=self._fmt_time(si["end_time"]) if si else None,
            check_in_time=self._fmt_dt(m["first_log"]),
            check_out_time=self._fmt_dt(m["last_log"]),
            working_hours=m["working_hours"],
            status=m["status"],
            is_late=m["late_minutes"] > 0,
            late_minutes=m["late_minutes"],
            shift_deficit_hours=m["shift_deficit_hours"],
            overtime_hours=m["overtime_hours"],
            worked_on_rest_day=m["worked_on_rest_day"],
            absent_days_count=absent,
            weekly_rest_days_count=weekly_rest,
            worked_on_rest_days_count=rest_work,
        )

    def build_monthly_summary_rows(self, db, department_id, start_date, end_date, branch_id=None):
        """Returns daily rows (row_kind=daily) + one summary per employee (row_kind=summary)."""
        emps = self._query_employees(db, department_id, branch_id)
        ids = [e.id for e in emps]
        log_map = self._build_log_map(db, ids, start_date, end_date)
        rec_map = self._build_record_map(db, ids, start_date, end_date)
        all_rows = []
        for emp in emps:
            wd = s1 = s2 = tl = rw = wr = ab = 0
            tot = 0.0
            dl = []
            for cur in self._iter_dates(start_date, end_date):
                m = self._day_metrics(emp, cur, rec_map.get((emp.id, cur)), log_map.get((emp.id, cur)))
                dl.append(m)
                if m["status"] == "present":
                    wd += 1
                    si = m["shift_info"]
                    if si:
                        if si.get("shift_category") == "shift_2":
                            s2 += 1
                        else:
                            s1 += 1
                    tl += m["late_minutes"]
                    tot += m["overtime_hours"]
                if m["worked_on_rest_day"]:
                    rw += 1
                elif m["status"] == "weekly_rest":
                    wr += 1
                elif m["status"] == "absent":
                    ab += 1
            for m in dl:
                all_rows.append(self._make_daily_row(emp, m, ab, wr, rw))
            all_rows.append(ReportRow(
                row_kind="summary",
                employee_code=emp.employee_code,
                employee_name=self._full_name(emp),
                department=emp.department.name if emp.department else None,
                job_title=emp.job_title,
                attendance_date="ملخص شهري",
                check_in_time=None,
                check_out_time=None,
                working_hours=0.0,
                status="monthly_summary",
                is_late=False,
                working_days_count=wd,
                shift_1_count=s1,
                shift_2_count=s2,
                total_late_minutes=tl,
                total_overtime_hours=round(tot, 2),
                worked_on_rest_days_count=rw,
                weekly_rest_days_count=wr,
                absent_days_count=ab,
            ))
        all_rows.sort(key=lambda r: (
            r.employee_name or "", r.employee_code or "",
            0 if r.row_kind == "summary" else 1, r.attendance_date,
        ))
        return all_rows

    def build_report_rows(self, db, department_id, start_date, end_date, branch_id=None):
        """Detailed daily report: one row per employee per day."""
        emps = self._query_employees(db, department_id, branch_id)
        ids = [e.id for e in emps]
        log_map = self._build_log_map(db, ids, start_date, end_date)
        rec_map = self._build_record_map(db, ids, start_date, end_date)
        rows = []
        for emp in emps:
            ab = wr = rw = 0
            dl = []
            for cur in self._iter_dates(start_date, end_date):
                m = self._day_metrics(emp, cur, rec_map.get((emp.id, cur)), log_map.get((emp.id, cur)))
                dl.append(m)
                if m["worked_on_rest_day"]:
                    rw += 1
                elif m["status"] == "weekly_rest":
                    wr += 1
                elif m["status"] == "absent":
                    ab += 1
            for m in dl:
                rows.append(self._make_daily_row(emp, m, ab, wr, rw))
        rows.sort(key=lambda r: (r.employee_name or "", r.employee_code or "", r.attendance_date))
        return rows

    def get_department_today_stats(self, db, department_id, branch_id=None):
        """Today live stats for department dashboard page."""
        today = date.today()
        emps = self._query_employees(db, department_id, branch_id)
        ids = [e.id for e in emps]
        log_map = self._build_log_map(db, ids, today, today)
        rec_map = self._build_record_map(db, ids, today, today)
        summ = []
        cnt = 0
        for emp in emps:
            m = self._day_metrics(emp, today, rec_map.get((emp.id, today)), log_map.get((emp.id, today)))
            si = m["shift_info"]
            if m["first_log"]:
                cnt += 1
            summ.append({
                "id": emp.id,
                "full_name": self._full_name(emp),
                "employee_code": emp.employee_code,
                "attendance_today": bool(m["first_log"]),
                "status": m["status"],
                "weekly_rest_day": emp.weekly_rest_day,
                "shift_name": si["label"] if si else None,
                "shift_type": si["shift_type"] if si else None,
                "check_in_time": self._fmt_dt(m["first_log"]),
                "check_out_time": self._fmt_dt(m["last_log"]),
                "working_hours": m["working_hours"],
                "late_minutes": m["late_minutes"],
                "shift_deficit_hours": m["shift_deficit_hours"],
                "overtime_hours": m["overtime_hours"],
                "worked_on_rest_day": m["worked_on_rest_day"],
            })
        lat = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.employee_id.in_(ids), AttendanceRecord.attendance_date == today)
            .order_by(AttendanceRecord.check_in_time.desc())
            .limit(10)
            .all()
        )
        return {
            "attendance_today": cnt,
            "employees": summ,
            "latest_attendance": [
                {
                    "employee_name": self._full_name(r.employee),
                    "check_in_time": self._fmt_dt(r.check_in_time),
                    "check_out_time": self._fmt_dt(r.check_out_time),
                    "working_hours": r.working_hours,
                }
                for r in lat
            ],
        }
