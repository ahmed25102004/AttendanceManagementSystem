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
        "وقت الحضور",
        "وقت الانصراف",
        "ساعات العمل",
        "الحالة",
        "متأخر",
    ]

    def _status_label(self, status: str) -> str:
        if status == "present":
            return "حاضر"
        if status == "absent":
            return "غائب"
        return status

    def export_excel(self, report_title: str, rows: list[ReportRow]) -> BytesIO:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "تقرير الحضور"
        sheet.append([report_title])
        sheet.append(self.headers)

        for row in rows:
            sheet.append(
                [
                    row.employee_code,
                    row.employee_name,
                    row.department or "",
                    row.job_title,
                    row.attendance_date,
                    row.check_in_time or "",
                    row.check_out_time or "",
                    row.working_hours,
                    self._status_label(row.status),
                    "نعم" if row.is_late else "لا",
                ]
            )

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
            table_data.append(
                [
                    row.employee_code,
                    row.employee_name,
                    row.department or "",
                    row.job_title,
                    row.attendance_date,
                    row.check_in_time or "",
                    row.check_out_time or "",
                    f"{row.working_hours:.2f}",
                    self._status_label(row.status),
                    "نعم" if row.is_late else "لا",
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
