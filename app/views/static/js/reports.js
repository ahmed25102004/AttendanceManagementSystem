let departmentsCache = [];
let currentSelectedDepartment = null;

function reportDepartmentQuery() {
    const departmentId = document.getElementById("reportDepartmentFilter")?.value;
    return departmentId ? `&department_id=${departmentId}` : "";
}

function isLeatherDepartment() {
    if (!currentSelectedDepartment) return false;
    const dept = departmentsCache.find(d => d.id === parseInt(currentSelectedDepartment));
    return dept && dept.attendance_policy === "leather_department";
}

function getReportStatusLabel(status) {
    const labels = {
        present: "حاضر",
        absent: "غائب",
        weekly_rest: "إجازة أسبوعية",
        present_on_rest_day: "حضر في يوم إجازته",
        monthly_summary: "ملخص شهري",
    };
    return labels[status] || status || "-";
}

async function loadDepartments() {
    departmentsCache = await fetchJSON("/api/departments");
    const select = document.getElementById("reportDepartmentFilter");
    if (!select) return;
    select.innerHTML = '<option value="">كل الأقسام</option>';
    departmentsCache.forEach((department) => {
        select.innerHTML += `<option value="${department.id}">${department.name}</option>`;
    });
    select.addEventListener("change", () => {
        currentSelectedDepartment = select.value;
        updateReportTableColumns();
    });
}

function isUnifiedDepartment() {
    if (!currentSelectedDepartment) return false;
    const dept = departmentsCache.find(d => d.id === parseInt(currentSelectedDepartment));
    return dept && (dept.attendance_policy === "reception_department" || dept.attendance_policy === "workers_department" || dept.attendance_policy === "doctors_department" || dept.attendance_policy === "leather_department");
}

function updateReportTableColumns() {
    const isLeather = isLeatherDepartment();
    const allTh = document.querySelectorAll("#reportTable thead tr th");
    
    // Column indices:  0:الكود,1:الاسم,2:القسم,3:المسمى الوظيفى,4:التاريخ,5:الشيفت,6:بداية الشيفت,7:نهاية الشيفت,8:وقت الحضور,9:وقت الانصراف,10:الساعات,11:ساعات العمل الإضافية,12:نقص الشيفت,13:التأخير,14:الحالة,15:عمل في الإجازة,16:أيام الغياب,17:الإجازات الأسبوعية,18:العمل في الإجازة
    let hideIndices = [];
    if (isLeather) {
        hideIndices = [5, 6, 7, 11, 12, 13, 16, 17, 18];
    }
    
    allTh.forEach((th, index) => {
        th.style.display = hideIndices.includes(index) ? "none" : "";
    });
    
    const allTd = document.querySelectorAll("#reportTable tbody tr td");
    allTd.forEach((td, index) => {
        const colIndex = index % allTh.length;
        td.style.display = hideIndices.includes(colIndex) ? "none" : "";
    });
}

async function renderReport(url) {
    const rows = await fetchJSON(url);
    const tbody = document.getElementById("reportTableBody");
    tbody.innerHTML = "";

    rows.forEach((row) => {
        const statusLabel = getReportStatusLabel(row.status);
        const rowClass = row.row_kind === "summary" ? "table-primary" : "";
        const overtimeValue = row.row_kind === "summary" ? row.total_overtime_hours : row.overtime_hours;
        tbody.innerHTML += `
            <tr class="${rowClass}">
                <td>${row.employee_code}</td>
                <td>${row.employee_name}</td>
                <td>${row.department || "-"}</td>
                <td>${row.job_title}</td>
                <td>${row.attendance_date}</td>
                                <td>${row.shift_name || "-"}</td>
                                <td>${row.shift_start_time || "-"}</td>
                                <td>${row.shift_end_time || "-"}</td>
                <td>${row.check_in_time ? new Date(row.check_in_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${row.check_out_time ? new Date(row.check_out_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${row.working_hours}</td>
                <td>${overtimeValue || 0}</td>
                <td>${row.shift_deficit_hours || 0}</td>
                                <td>${row.late_minutes || 0}</td>
                <td>${statusLabel}</td>
                                <td>${row.worked_on_rest_day ? "نعم" : "لا"}</td>
                                <td>${row.absent_days_count || 0}</td>
                                <td>${row.weekly_rest_days_count || 0}</td>
                                <td>${row.worked_on_rest_days_count || 0}</td>
            </tr>
        `;
    });
    
    updateReportTableColumns();
}

function securedDownload(path) {
    const token = getToken();
    fetch(path, {
        headers: { Authorization: `Bearer ${token}` },
    })
        .then(async (response) => {
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "فشل تنزيل الملف.");
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            const disposition = response.headers.get("Content-Disposition") || "";
            const fileNameMatch = disposition.match(/filename="(.+)"/);
            link.download = fileNameMatch ? fileNameMatch[1] : "report";
            link.click();
            window.URL.revokeObjectURL(url);
        })
        .catch((error) => showAlert("reportAlert", error.message));
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadDepartments();

    document.getElementById("dailyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("daily_report_date").value;
        try {
            await renderReport(`/api/reports/daily?report_date=${reportDate}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("weeklyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("weekly_report_date").value;
        try {
            await renderReport(`/api/reports/weekly?report_date=${reportDate}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("monthlyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const month = document.getElementById("monthly_report_month").value;
        try {
            await renderReport(`/api/reports/monthly?month=${month}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("exportDailyExcel").addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/excel?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportDailyPdf").addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/pdf?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportWeeklyExcel").addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/excel?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportWeeklyPdf").addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/pdf?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportMonthlyExcel").addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        securedDownload(`/api/reports/monthly/export/excel?month=${month}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportMonthlyPdf").addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        securedDownload(`/api/reports/monthly/export/pdf?month=${month}${reportDepartmentQuery()}`);
    });
});
