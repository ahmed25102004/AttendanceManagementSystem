let departmentsCache = [];
let currentSelectedDepartment = null;
let currentReportData = []; 
let currentViewMode = "daily"; // "daily", "summary", or "details"
let currentDetailedEmployeeCode = null;

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
    select.innerHTML = '<option value="">— كل الأقسام —</option>';
    departmentsCache.forEach((department) => {
        select.innerHTML += `<option value="${department.id}">${department.name}</option>`;
    });
    select.addEventListener("change", () => {
        currentSelectedDepartment = select.value;
        updateReportTableColumns();
    });
}

function updateReportTableColumns() {
    const isLeather = isLeatherDepartment();
    let hiddenByPolicy = [];
    
    // Hide specific columns for leather department
    if (isLeather) {
        hiddenByPolicy = [
            "shift_name",
            "shift_start_time",
            "shift_end_time",
            "overtime_hours",
            "shift_deficit_hours",
            "late_minutes",
            "absent_days_count",
            "weekly_rest_days_count",
            "worked_on_rest_days_count",
            "shift_1_count",
            "shift_2_count"
        ];
    }

    if (currentViewMode === "summary") {
        hiddenByPolicy.push(
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "shift_deficit_hours", "status", "worked_on_rest_day"
        );
    } else {
        hiddenByPolicy.push(
            "absent_days_count", "weekly_rest_days_count", "worked_on_rest_days_count",
            "shift_1_count", "shift_2_count"
        );
    }

    const allColumns = document.querySelectorAll("#reportTable th[data-column]");
    allColumns.forEach((th) => {
        const columnName = th.dataset.column;
        const checkbox = document.querySelector(`.col-toggle[data-column="${columnName}"]`);
        
        let isVisible = true;
        
        if (hiddenByPolicy.includes(columnName)) {
            isVisible = false;
        } else if (checkbox && !checkbox.checked) {
            isVisible = false;
        }

        th.style.display = isVisible ? "" : "none";
        
        const tds = document.querySelectorAll(`#reportTableBody td[data-column="${columnName}"]`);
        tds.forEach(td => td.style.display = isVisible ? "" : "none");
    });
}

function setupColumnVisibilityMenu() {
    const menu = document.getElementById("columnVisibilityMenu");
    if (!menu) return;
    const headers = document.querySelectorAll("#reportTable th[data-column]");
    menu.innerHTML = "";
    
    headers.forEach(th => {
        const col = th.dataset.column;
        const label = th.dataset.label;
        
        const hideByDefault = [
            "department", 
            "job_title", 
            "attendance_date",
            "shift_name", 
            "shift_start_time", 
            "shift_end_time", 
            "absent_days_count",
            "weekly_rest_days_count",
            "worked_on_rest_days_count",
            "shift_1_count",
            "shift_2_count"
        ];
        const checked = hideByDefault.includes(col) ? "" : "checked";
        
        const li = document.createElement("li");
        li.innerHTML = `
            <label class="dropdown-item d-flex align-items-center gap-2">
                <input class="form-check-input col-toggle" type="checkbox" value="" data-column="${col}" ${checked}>
                ${label}
            </label>
        `;
        menu.appendChild(li);
    });

    menu.addEventListener('click', function (e) {
        e.stopPropagation();
    });

    document.querySelectorAll('.col-toggle').forEach(chk => {
        chk.addEventListener('change', updateReportTableColumns);
    });
}

function updateSummaryCards(rows) {
    const cardsContainer = document.getElementById("summaryCards");
    if (cardsContainer) cardsContainer.style.display = "flex";
    
    let totalRows = 0;
    let present = 0;
    let absent = 0;
    let lateCount = 0;
    let totalLateMinutes = 0;
    let totalOvertime = 0;
    let restDayWork = 0;

    rows.forEach(row => {
        if (row.row_kind === "summary") return; 
        
        totalRows++;
        
        if (row.status === "present" || row.status === "present_on_rest_day") present++;
        if (row.status === "absent") absent++;
        
        if (row.late_minutes > 0) {
            lateCount++;
            totalLateMinutes += row.late_minutes;
        }
        
        if (row.overtime_hours > 0) {
            totalOvertime += parseFloat(row.overtime_hours);
        }
        
        if (row.worked_on_rest_day) {
            restDayWork++;
        }
    });

    document.getElementById("statTotalRows").innerText = totalRows;
    document.getElementById("statPresent").innerText = present;
    document.getElementById("statAbsent").innerText = absent;
    document.getElementById("statLateCount").innerText = lateCount;
    document.getElementById("statLateMinutes").innerText = totalLateMinutes + " دقيقة";
    document.getElementById("statOvertime").innerText = totalOvertime.toFixed(2);
    document.getElementById("statRestDay").innerText = restDayWork;
}

function filterTable(searchTerm) {
    if (!searchTerm) {
        renderTableBody(currentReportData);
        return;
    }
    
    searchTerm = searchTerm.toLowerCase();
    const filteredRows = currentReportData.filter(row => {
        return (row.employee_name && row.employee_name.toLowerCase().includes(searchTerm)) || 
               (row.employee_code && row.employee_code.toString().toLowerCase().includes(searchTerm)) ||
               (row.department && row.department.toLowerCase().includes(searchTerm));
    });
    
    renderTableBody(filteredRows);
}

function renderTableBody(rows) {
    const tbody = document.getElementById("reportTableBody");
    tbody.innerHTML = "";

    let rowsToRender = rows;
    if (currentViewMode === "summary") {
        rowsToRender = rows.filter(r => r.row_kind === "summary");
    } else if (currentViewMode === "details" && currentDetailedEmployeeCode) {
        rowsToRender = rows.filter(r => r.row_kind !== "summary" && r.employee_code === currentDetailedEmployeeCode);
    } else {
        rowsToRender = rows.filter(r => r.row_kind !== "summary");
    }

    const btnBackToSummary = document.getElementById("btnBackToSummary");
    if (btnBackToSummary) {
        btnBackToSummary.style.display = currentViewMode === "details" ? "inline-block" : "none";
    }

    if (rowsToRender.length === 0) {
        tbody.innerHTML = `
            <tr id="emptyRowTr">
                <td colspan="21" class="text-center py-5 text-muted">
                    <i class="bi bi-search fs-1 d-block mb-2 opacity-50"></i>
                    <strong>لا توجد نتائج لعرضها</strong>
                </td>
            </tr>
        `;
        updateReportTableColumns();
        return;
    }

    rowsToRender.forEach((row) => {
        const statusLabel = getReportStatusLabel(row.status);
        
        let trClass = "";
        let lateClass = "";
        let overtimeClass = "";
        
        if (row.row_kind === "summary") {
            trClass = "table-primary fw-bold";
        } else {
            if (row.status === "absent") trClass = "table-danger";
            else if (row.worked_on_rest_day) trClass = "table-secondary";
            
            if (row.late_minutes > 0) lateClass = "text-danger fw-bold";
            if (row.overtime_hours > 0) overtimeClass = "text-success fw-bold";
        }

        const overtimeValue = row.row_kind === "summary" ? row.total_overtime_hours : row.overtime_hours;
        
        let statusBadgeClass = "bg-secondary";
        if (row.status === 'present') statusBadgeClass = 'bg-success';
        else if (row.status === 'absent') statusBadgeClass = 'bg-danger';
        else if (row.status === 'weekly_rest') statusBadgeClass = 'bg-info text-dark';
        else if (row.status === 'present_on_rest_day') statusBadgeClass = 'bg-warning text-dark';

        // Format dates cleanly
        let checkIn = "-";
        if (row.check_in_time) {
            checkIn = new Date(row.check_in_time).toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
        }
        let checkOut = "-";
        if (row.check_out_time) {
            checkOut = new Date(row.check_out_time).toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
        }
        
        let nameHtml = `<strong>${row.employee_name || "-"}</strong>`;
        if (currentViewMode === "summary") {
            nameHtml = `<a href="#" class="employee-detail-link fw-bold text-decoration-none" data-code="${row.employee_code}">${row.employee_name || "-"}</a>`;
        }

        tbody.innerHTML += `
            <tr class="${trClass}">
                <td data-column="employee_code">${row.employee_code || "-"}</td>
                <td data-column="employee_name">${nameHtml}</td>
                <td data-column="department"><span class="badge bg-light text-dark border">${row.department || "-"}</span></td>
                <td data-column="job_title" class="text-muted small">${row.job_title || "-"}</td>
                <td data-column="attendance_date">${row.attendance_date || "-"}</td>
                <td data-column="shift_name">${row.shift_name || "-"}</td>
                <td data-column="shift_start_time">${row.shift_start_time || "-"}</td>
                <td data-column="shift_end_time">${row.shift_end_time || "-"}</td>
                <td data-column="check_in_time">${checkIn}</td>
                <td data-column="check_out_time">${checkOut}</td>
                <td data-column="working_hours">${row.working_hours || 0}</td>
                <td data-column="overtime_hours" class="${overtimeClass}">${overtimeValue || 0}</td>
                <td data-column="shift_deficit_hours">${row.shift_deficit_hours || 0}</td>
                <td data-column="late_minutes" class="${lateClass}">${row.late_minutes || 0}</td>
                <td data-column="status"><span class="badge ${statusBadgeClass}">${statusLabel}</span></td>
                <td data-column="worked_on_rest_day">${row.worked_on_rest_day ? '<i class="bi bi-check-circle-fill text-success"></i>' : '-'}</td>
                <td data-column="absent_days_count">${row.absent_days_count || 0}</td>
                <td data-column="weekly_rest_days_count">${row.weekly_rest_days_count || 0}</td>
                <td data-column="shift_1_count">${row.shift_1_count || 0}</td>
                <td data-column="shift_2_count">${row.shift_2_count || 0}</td>
                <td data-column="worked_on_rest_days_count">${row.worked_on_rest_days_count || 0}</td>
            </tr>
        `;
    });
    
    if (currentViewMode === "summary") {
        document.querySelectorAll(".employee-detail-link").forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                currentDetailedEmployeeCode = e.target.dataset.code;
                currentViewMode = "details";
                renderTableBody(currentReportData);
            });
        });
    }

    updateReportTableColumns();
}

async function renderReport(url) {
    try {
        const rows = await fetchJSON(url);
        currentReportData = rows;
        
        const hasSummary = rows.some(r => r.row_kind === "summary");
        currentViewMode = hasSummary ? "summary" : "daily";
        currentDetailedEmployeeCode = null;

        const searchBox = document.getElementById("reportSearchBox");
        if(searchBox) searchBox.value = ""; 
        
        updateSummaryCards(rows);
        renderTableBody(rows);
    } catch (error) {
        throw error;
    }
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
    setupColumnVisibilityMenu();
    updateReportTableColumns(); // initial hide of clutter

    // Setup live search
    const searchBox = document.getElementById("reportSearchBox");
    if (searchBox) {
        searchBox.addEventListener("input", (e) => {
            filterTable(e.target.value);
        });
    }

    const btnBackToSummary = document.getElementById("btnBackToSummary");
    if (btnBackToSummary) {
        btnBackToSummary.addEventListener("click", () => {
            currentViewMode = "summary";
            currentDetailedEmployeeCode = null;
            const searchTerm = searchBox ? searchBox.value : "";
            filterTable(searchTerm);
        });
    }

    const clearSearchBtn = document.getElementById("clearReportSearchBtn");
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", () => {
            if (searchBox) {
                searchBox.value = "";
                filterTable("");
            }
        });
    }

    // Quick Date Buttons
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("quickTodayBtn")?.addEventListener("click", () => {
        const tab = new bootstrap.Tab(document.querySelector('#daily-tab'));
        tab.show();
        document.getElementById("daily_report_date").value = today;
        document.getElementById("dailyReportForm").dispatchEvent(new Event("submit"));
    });

    document.getElementById("quickWeekBtn")?.addEventListener("click", () => {
        const tab = new bootstrap.Tab(document.querySelector('#weekly-tab'));
        tab.show();
        document.getElementById("weekly_report_date").value = today;
        document.getElementById("weeklyReportForm").dispatchEvent(new Event("submit"));
    });

    document.getElementById("quickMonthBtn")?.addEventListener("click", () => {
        const tab = new bootstrap.Tab(document.querySelector('#monthly-tab'));
        tab.show();
        const currentMonth = today.substring(0, 7);
        document.getElementById("monthly_report_month").value = currentMonth;
        document.getElementById("monthlyReportForm").dispatchEvent(new Event("submit"));
    });

    document.getElementById("dailyReportForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("daily_report_date").value;
        try {
            await renderReport(`/api/reports/daily?report_date=${reportDate}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("weeklyReportForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("weekly_report_date").value;
        try {
            await renderReport(`/api/reports/weekly?report_date=${reportDate}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("monthlyReportForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const month = document.getElementById("monthly_report_month").value;
        try {
            await renderReport(`/api/reports/monthly?month=${month}${reportDepartmentQuery()}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("exportDailyExcel")?.addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/excel?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportDailyPdf")?.addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/pdf?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportWeeklyExcel")?.addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/excel?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportWeeklyPdf")?.addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/pdf?report_date=${reportDate}${reportDepartmentQuery()}`);
    });

    document.getElementById("exportMonthlyExcel")?.addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        let query = `/api/reports/monthly/export/excel?month=${month}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
        if (currentViewMode === "details" && currentDetailedEmployeeCode) {
            query += `&employee_code=${currentDetailedEmployeeCode}`;
        }
        securedDownload(query);
    });

    document.getElementById("exportMonthlyPdf")?.addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        let query = `/api/reports/monthly/export/pdf?month=${month}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
        if (currentViewMode === "details" && currentDetailedEmployeeCode) {
            query += `&employee_code=${currentDetailedEmployeeCode}`;
        }
        securedDownload(query);
    });
});
