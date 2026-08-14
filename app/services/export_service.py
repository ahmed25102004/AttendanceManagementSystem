from io import BytesIO

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.report import ReportRow


class ExportService:
    headers = [
        "كود الموظف",
        "اسم الموظف",
        "القسم",
        "المسمى الوظيفي",
        "تاريخ الحضور",
        "الشيفت",
        "بداية الشيفت",
        "نهاية الشيفت",
        "وقت الحضور",
        "وقت الانصراف",
        "ساعات العمل",
        "ساعات العمل الإضافي",
        "دقائق التأخير",
        "الحالة",
        "عمل في الإجازة",
        "أيام الغياب",
        "أيام الإجازة الأسبوعية",
        "أيام العمل في الإجازة",
    ]

    def _status_label(self, status: str) -> str:
        if status == "present":
            return "حاضر"
        if status == "absent":
            return "غائب"
        if status == "weekly_rest":
            return "إجازة أسبوعية"
        if status == "present_on_rest_day":
            return "حضر في يوم إجازته"
        if status == "monthly_summary":
            return "ملخص شهري"
        return status

    def export_excel(self, report_title: str, rows: list[ReportRow]) -> BytesIO:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "تقرير الحضور"
        sheet.append([report_title])
        sheet.append(self.headers)

        for row in rows:
            overtime_value = row.total_overtime_hours if row.row_kind == "summary" else row.overtime_hours
            sheet.append(
                [
                    row.employee_code,
                    row.employee_name,
                    row.department or "",
                    row.job_title,
                    row.attendance_date,
                    row.shift_name or "",
                    row.shift_start_time or "",
                    row.shift_end_time or "",
                    row.check_in_time or "",
                    row.check_out_time or "",
                    row.working_hours,
                    overtime_value,
                    row.late_minutes,
                    self._status_label(row.status),
                    "نعم" if row.worked_on_rest_day else "لا",
                    row.absent_days_count,
                    row.weekly_rest_days_count,
                    row.worked_on_rest_days_count,
                ]
            )

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    def export_policy_summary_excel(self, report_title: str, rows: list[ReportRow], policy: str) -> BytesIO:
        """Export simplified monthly summary tailored to the department policy."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "ملخص الحضور"
        sheet.append([report_title])

        summary_rows = [r for r in rows if r.row_kind == "summary"]

        if policy == "leather_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي ساعات العمل", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.working_days_count, r.working_hours, r.absent_days_count])

        elif policy == "doctors_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "شفت كامل", "نصف شفت", "إجمالي الشيفتات", "ساعات العمل", "إجمالي الإضافي (س)", "إجمالي التأخير (د)", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.full_shift_count, r.half_shift_count, r.total_shift_units, r.working_hours, r.total_overtime_hours, r.total_late_minutes, r.absent_days_count])

        elif policy == "call_center_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "شيفت صباحي", "شيفت مسائي", "إجمالي التأخير (د)", "إجمالي الإضافي (س)", "عمل في إجازة", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.working_days_count, r.shift_1_count, r.shift_2_count, r.total_late_minutes, r.total_overtime_hours, r.worked_on_rest_days_count, r.absent_days_count])

        elif policy == "workers_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "شيفت صباحي", "شيفت مسائي", "إجمالي التأخير (د)", "إجمالي الإضافي (س)", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.working_days_count, r.shift_1_count, r.shift_2_count, r.total_late_minutes, r.total_overtime_hours, r.worked_on_rest_days_count, r.weekly_rest_days_count, r.absent_days_count])

        elif policy == "reception_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي ساعات العمل", "إجمالي التأخير (د)", "إجمالي الإضافي (س)", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.working_days_count, r.working_hours, r.total_late_minutes, r.total_overtime_hours, r.worked_on_rest_days_count, r.weekly_rest_days_count, r.absent_days_count])

        else:
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي الساعات", "إجمالي الشيفتات", "إجمالي التأخير (د)", "إجمالي الإضافي (س)", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            sheet.append(headers)
            for r in summary_rows:
                sheet.append([r.employee_code, r.employee_name, r.department or "", r.job_title, r.working_days_count, r.working_hours, r.total_shift_units, r.total_late_minutes, r.total_overtime_hours, r.worked_on_rest_days_count, r.weekly_rest_days_count, r.absent_days_count])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    def export_pdf(self, report_title: str, rows: list[ReportRow]) -> BytesIO:
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=landscape(A4))
        styles = getSampleStyleSheet()

        table_data = [self.headers]
        for row in rows:
            overtime_value = row.total_overtime_hours if row.row_kind == "summary" else row.overtime_hours
            table_data.append(
                [
                    row.employee_code,
                    row.employee_name,
                    row.department or "",
                    row.job_title,
                    row.attendance_date,
                    row.shift_name or "",
                    row.shift_start_time or "",
                    row.shift_end_time or "",
                    row.check_in_time or "",
                    row.check_out_time or "",
                    f"{row.working_hours:.2f}",
                    f"{overtime_value:.2f}",
                    row.late_minutes,
                    self._status_label(row.status),
                    "نعم" if row.worked_on_rest_day else "لا",
                    row.absent_days_count,
                    row.weekly_rest_days_count,
                    row.worked_on_rest_days_count,
                ]
            )

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements = [
            Paragraph(report_title, styles["Title"]),
            Spacer(1, 12),
            table,
        ]
        document.build(elements)
        output.seek(0)
        return output

    def export_policy_summary_pdf(self, report_title: str, rows: list[ReportRow], policy: str) -> BytesIO:
        """PDF export tailored to department policy in summary mode."""
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=landscape(A4))
        styles = getSampleStyleSheet()

        summary_rows = [r for r in rows if r.row_kind == "summary"]

        if policy == "leather_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي ساعات العمل", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.working_days_count), f"{r.working_hours:.2f}", str(r.absent_days_count)])

        elif policy == "doctors_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "شفت كامل", "نصف شفت", "إجمالي الشيفتات", "ساعات العمل", "إجمالي الإضافي", "إجمالي التأخير", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.full_shift_count), str(r.half_shift_count), str(r.total_shift_units), f"{r.working_hours:.2f}", f"{r.total_overtime_hours:.2f}", str(r.total_late_minutes), str(r.absent_days_count)])

        elif policy == "call_center_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "شيفت صباحي", "شيفت مسائي", "إجمالي التأخير", "إجمالي الإضافي", "عمل في إجازة", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.working_days_count), str(r.shift_1_count), str(r.shift_2_count), str(r.total_late_minutes), f"{r.total_overtime_hours:.2f}", str(r.worked_on_rest_days_count), str(r.absent_days_count)])

        elif policy == "workers_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "شيفت صباحي", "شيفت مسائي", "إجمالي التأخير", "إجمالي الإضافي", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.working_days_count), str(r.shift_1_count), str(r.shift_2_count), str(r.total_late_minutes), f"{r.total_overtime_hours:.2f}", str(r.worked_on_rest_days_count), str(r.weekly_rest_days_count), str(r.absent_days_count)])

        elif policy == "reception_department":
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي ساعات العمل", "إجمالي التأخير", "إجمالي الإضافي", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.working_days_count), f"{r.working_hours:.2f}", str(r.total_late_minutes), f"{r.total_overtime_hours:.2f}", str(r.worked_on_rest_days_count), str(r.weekly_rest_days_count), str(r.absent_days_count)])

        else:
            headers = ["كود الموظف", "اسم الموظف", "القسم", "المسمى الوظيفي", "أيام العمل", "إجمالي الساعات", "إجمالي الشيفتات", "إجمالي التأخير", "إجمالي الإضافي", "عمل في إجازة", "الإجازات الأسبوعية", "أيام الغياب"]
            table_data = [headers]
            for r in summary_rows:
                table_data.append([r.employee_code, r.employee_name, r.department or "", r.job_title, str(r.working_days_count), f"{r.working_hours:.2f}", str(r.total_shift_units), str(r.total_late_minutes), f"{r.total_overtime_hours:.2f}", str(r.worked_on_rest_days_count), str(r.weekly_rest_days_count), str(r.absent_days_count)])

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements = [
            Paragraph(report_title, styles["Title"]),
            Spacer(1, 12),
            table,
        ]
        document.build(elements)
        output.seek(0)
        return output
