let departmentsCache = [];
let currentSelectedDepartment = null;
let currentReportData = []; 
let currentViewMode = "daily"; // "daily", "summary", or "details"
let currentDetailedEmployeeCode = null;

function reportDepartmentQuery() {
    const departmentId = document.getElementById("reportDepartmentFilter")?.value;
    return departmentId ? `&department_id=${departmentId}` : "";
}

function getSelectedPolicy() {
    if (!currentSelectedDepartment) return "default";
    const dept = departmentsCache.find(d => d.id === parseInt(currentSelectedDepartment));
    return dept ? dept.attendance_policy : "default";
}

const POLICY_COLUMNS = {
    // 1. Leather Department: Hours only, no shifts, no late, no overtime
    leather_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "check_in_time", "check_out_time", "working_hours", "status"
        ]
    },
    // 2. Doctors Department: Full shift, half shift, total units, hours, overtime, late, absent
    doctors_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "full_shift_count", "half_shift_count", "total_shift_units", 
            "working_hours", "overtime_hours", "late_minutes", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "check_in_time", "check_out_time", 
            "working_hours", "overtime_hours", "shift_deficit_hours", "late_minutes", "status"
        ]
    },
    // 3. Call Center: Working days, shift 1, shift 2, late, overtime, rest day work, absent
    call_center_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "shift_1_count", "shift_2_count", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "shift_deficit_hours", "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    // 4. Workers: Working days, shift 1, shift 2, late, overtime, rest day work, weekly rest, absent
    workers_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "shift_1_count", "shift_2_count", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", 
            "weekly_rest_days_count", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "shift_deficit_hours", "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    // 5. Reception: Working days, working hours, late, overtime, rest day work, weekly rest, absent
    reception_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "late_minutes", "overtime_hours", 
            "worked_on_rest_days_count", "weekly_rest_days_count", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    // 6. Default / All departments
    default: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "total_shift_units", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", 
            "weekly_rest_days_count", "absent_days_count"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "check_in_time", "check_out_time", 
            "working_hours", "overtime_hours", "late_minutes", "status", "worked_on_rest_day"
        ]
    }
};

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
        setupColumnVisibilityMenu();
        updateReportTableColumns();
    });
}

function updateReportTableColumns() {
    const policy = getSelectedPolicy();
    const config = POLICY_COLUMNS[policy] || POLICY_COLUMNS.default;
    const mode = currentViewMode === "summary" ? "summary" : "daily";
    const allowedColumns = config[mode] || config.daily;

    const allColumns = document.querySelectorAll("#reportTable th[data-column]");
    allColumns.forEach((th) => {
        const columnName = th.dataset.column;
        const checkbox = document.querySelector(`.col-toggle[data-column="${columnName}"]`);
        
        let isVisible = allowedColumns.includes(columnName);
        
        if (checkbox && !checkbox.checked) {
            isVisible = false;
        }

        th.style.display = isVisible ? "" : "none";
        
        const tds = document.querySelectorAll(`#reportTableBody td[data-column="${columnName}"]`);
        tds.forEach(td => td.style.display = isVisible ? "" : "none");
    });

    // Update Header Labels based on mode
    const isSummary = currentViewMode === "summary";
    const overtimeTh = document.querySelector("#reportTable th[data-column='overtime_hours']");
    const lateTh = document.querySelector("#reportTable th[data-column='late_minutes']");
    const hoursTh = document.querySelector("#reportTable th[data-column='working_hours']");
    
    if (overtimeTh) {
        overtimeTh.textContent = isSummary ? "إجمالي الإضافي (س)" : "ساعات العمل الإضافي";
    }
    if (lateTh) {
        lateTh.textContent = isSummary ? "إجمالي التأخير (د)" : "التأخير";
    }
    if (hoursTh) {
        hoursTh.textContent = isSummary ? "إجمالي الساعات" : "الساعات";
    }
}

function setupColumnVisibilityMenu() {
    const menu = document.getElementById("columnVisibilityMenu");
    if (!menu) return;
    const headers = document.querySelectorAll("#reportTable th[data-column]");
    menu.innerHTML = "";
    
    const policy = getSelectedPolicy();
    const config = POLICY_COLUMNS[policy] || POLICY_COLUMNS.default;
    const mode = currentViewMode === "summary" ? "summary" : "daily";
    const allowedColumns = config[mode] || config.daily;

    headers.forEach(th => {
        const col = th.dataset.column;
        const label = th.dataset.label;
        const isDefaultVisible = allowedColumns.includes(col);
        const checked = isDefaultVisible ? "checked" : "";
        
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
                <td colspan="25" class="text-center py-5 text-muted">
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

        const isSummary = row.row_kind === "summary";
        const overtimeValue = isSummary
            ? (row.total_overtime_hours ?? 0)
            : (row.overtime_hours ?? 0);
        const lateValue = isSummary
            ? (row.total_late_minutes ?? 0)
            : (row.late_minutes ?? 0);
        
        let statusBadgeClass = "bg-secondary";
        if (row.status === 'present') statusBadgeClass = 'bg-success';
        else if (row.status === 'absent') statusBadgeClass = 'bg-danger';
        else if (row.status === 'weekly_rest') statusBadgeClass = 'bg-info text-dark';
        else if (row.status === 'present_on_rest_day') statusBadgeClass = 'bg-warning text-dark';
        else if (row.status === 'monthly_summary') statusBadgeClass = 'bg-primary';

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
                <td data-column="working_days_count"><span class="badge bg-primary bg-opacity-75">${row.working_days_count || 0} يوم</span></td>
                <td data-column="shift_name">${row.shift_name || "-"}</td>
                <td data-column="shift_start_time">${row.shift_start_time || "-"}</td>
                <td data-column="shift_end_time">${row.shift_end_time || "-"}</td>
                <td data-column="check_in_time">${checkIn}</td>
                <td data-column="check_out_time">${checkOut}</td>
                <td data-column="working_hours">${row.working_hours || 0}</td>
                <td data-column="overtime_hours" class="${overtimeClass}">${overtimeValue}</td>
                <td data-column="shift_deficit_hours">${row.shift_deficit_hours || 0}</td>
                <td data-column="late_minutes" class="${lateClass}">${lateValue}</td>
                <td data-column="status"><span class="badge ${statusBadgeClass}">${statusLabel}</span></td>
                <td data-column="worked_on_rest_day">${row.worked_on_rest_day ? '<i class="bi bi-check-circle-fill text-success"></i>' : '-'}</td>
                <td data-column="full_shift_count">${row.full_shift_count || 0}</td>
                <td data-column="half_shift_count">${row.half_shift_count || 0}</td>
                <td data-column="total_shift_units"><span class="badge bg-info text-dark">${row.total_shift_units || 0}</span></td>
                <td data-column="shift_1_count">${row.shift_1_count || 0}</td>
                <td data-column="shift_2_count">${row.shift_2_count || 0}</td>
                <td data-column="worked_on_rest_days_count">${row.worked_on_rest_days_count || 0}</td>
                <td data-column="weekly_rest_days_count">${row.weekly_rest_days_count || 0}</td>
                <td data-column="absent_days_count">${row.absent_days_count || 0}</td>
            </tr>
        `;
    });
    
    if (currentViewMode === "summary") {
        document.querySelectorAll(".employee-detail-link").forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                currentDetailedEmployeeCode = e.target.dataset.code;
                currentViewMode = "details";
                setupColumnVisibilityMenu();
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
        
        setupColumnVisibilityMenu();
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
    updateReportTableColumns();

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
            setupColumnVisibilityMenu();
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

    // Set default input values
    const today = new Date().toISOString().split('T')[0];
    const currentMonth = today.substring(0, 7);
    if (document.getElementById("daily_report_date")) document.getElementById("daily_report_date").value = today;
    if (document.getElementById("weekly_report_date")) document.getElementById("weekly_report_date").value = today;
    if (document.getElementById("monthly_report_month")) document.getElementById("monthly_report_month").value = currentMonth;

    // Quick Date Buttons
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

    function normalizeMonthInput(value) {
        if (!value) return "";
        value = value.trim().replace("/", "-");
        const parts = value.split("-");
        if (parts.length === 2) {
            if (parts[0].length === 4) {
                return `${parts[0]}-${parts[1].padStart(2, '0')}`;
            } else if (parts[1].length === 4) {
                return `${parts[1]}-${parts[0].padStart(2, '0')}`;
            }
        }
        return value;
    }

    document.getElementById("monthlyReportForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const rawMonth = document.getElementById("monthly_report_month").value;
        const month = normalizeMonthInput(rawMonth);
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
        const rawMonth = document.getElementById("monthly_report_month").value;
        const month = normalizeMonthInput(rawMonth);
        let query = `/api/reports/monthly/export/excel?month=${month}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
        if (currentViewMode === "details" && currentDetailedEmployeeCode) {
            query += `&employee_code=${currentDetailedEmployeeCode}`;
        }
        securedDownload(query);
    });

    document.getElementById("exportMonthlyPdf")?.addEventListener("click", () => {
        const rawMonth = document.getElementById("monthly_report_month").value;
        const month = normalizeMonthInput(rawMonth);
        let query = `/api/reports/monthly/export/pdf?month=${month}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
        if (currentViewMode === "details" && currentDetailedEmployeeCode) {
            query += `&employee_code=${currentDetailedEmployeeCode}`;
        }
        securedDownload(query);
    });
});
