let departmentsCache = [];
let currentSelectedDepartment = null;
let currentReportData = []; 
let currentViewMode = "summary"; // "summary", "daily", or "details"
let currentDetailedEmployeeCode = null;
let currentPeriod = "custom"; // "custom", "daily", "weekly", or "monthly"

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
    leather_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "absent_days_count", "actions"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "check_in_time", "check_out_time", "working_hours", "status"
        ]
    },
    doctors_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "full_shift_count", "half_shift_count", "total_shift_units", 
            "working_hours", "overtime_hours", "late_minutes", "absent_days_count", "actions"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "check_in_time", "check_out_time", 
            "working_hours", "overtime_hours", "shift_deficit_hours", "late_minutes", "status"
        ]
    },
    call_center_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "shift_1_count", "shift_2_count", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", "absent_days_count", "actions"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "shift_deficit_hours", "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    workers_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "shift_1_count", "shift_2_count", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", 
            "weekly_rest_days_count", "absent_days_count", "actions"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "shift_deficit_hours", "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    reception_department: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "late_minutes", "overtime_hours", 
            "worked_on_rest_days_count", "weekly_rest_days_count", "absent_days_count", "actions"
        ],
        daily: [
            "employee_code", "employee_name", "department", "job_title", 
            "attendance_date", "shift_name", "shift_start_time", "shift_end_time", 
            "check_in_time", "check_out_time", "working_hours", "overtime_hours", 
            "late_minutes", "status", "worked_on_rest_day"
        ]
    },
    default: {
        summary: [
            "employee_code", "employee_name", "department", "job_title", 
            "working_days_count", "working_hours", "total_shift_units", 
            "late_minutes", "overtime_hours", "worked_on_rest_days_count", 
            "weekly_rest_days_count", "absent_days_count", "actions"
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
        monthly_summary: "ملخص الفترة",
    };
    return labels[status] || status || "-";
}

async function loadDepartments() {
    try {
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
    } catch (e) {
        console.warn("Could not load departments:", e);
    }
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
        
        const isVisible = checkbox ? checkbox.checked : allowedColumns.includes(columnName);

        th.style.display = isVisible ? "" : "none";
        
        const tds = document.querySelectorAll(`#reportTableBody td[data-column="${columnName}"]`);
        tds.forEach(td => td.style.display = isVisible ? "" : "none");
    });

    const isSummary = currentViewMode === "summary";
    const overtimeTh = document.querySelector("#reportTable th[data-column='overtime_hours']");
    const lateTh = document.querySelector("#reportTable th[data-column='late_minutes']");
    const hoursTh = document.querySelector("#reportTable th[data-column='working_hours']");
    
    if (overtimeTh) overtimeTh.textContent = isSummary ? "إجمالي الإضافي (س)" : "ساعات العمل الإضافي";
    if (lateTh) lateTh.textContent = isSummary ? "إجمالي التأخير (د)" : "التأخير";
    if (hoursTh) hoursTh.textContent = isSummary ? "إجمالي الساعات" : "الساعات";
}

let columnMenuInitialized = false;

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
            <label class="dropdown-item d-flex align-items-center gap-2 small py-1">
                <input class="form-check-input col-toggle" type="checkbox" value="" data-column="${col}" ${checked}>
                ${label}
            </label>
        `;
        menu.appendChild(li);
    });

    if (!columnMenuInitialized) {
        menu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
        columnMenuInitialized = true;
    }

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
        rowsToRender = rows.filter(r => r.row_kind !== "summary" && String(r.employee_code) === String(currentDetailedEmployeeCode));
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
                <td colspan="26" class="text-center py-5 text-muted">
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
            trClass = "report-row-summary";
        } else {
            trClass = "report-row-daily";
            if (row.status === "absent") trClass += " report-row-absent";
            
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

        let checkIn = "-";
        if (row.check_in_time) {
            const d = new Date(row.check_in_time);
            checkIn = isNaN(d.getTime()) ? row.check_in_time : d.toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
        }
        let checkOut = "-";
        if (row.check_out_time) {
            const d = new Date(row.check_out_time);
            checkOut = isNaN(d.getTime()) ? row.check_out_time : d.toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
        }
        
        let nameHtml = `<strong class="text-white">${row.employee_name || "-"}</strong>`;
        let actionsHtml = "-";
        if (isSummary) {
            actionsHtml = `
                <button type="button" class="btn btn-sm btn-report-details rounded-pill px-3 shadow-sm btn-open-emp-modal text-nowrap" data-code="${row.employee_code}" title="عرض تفاصيل بصمات وساعات وحضور الموظف في الفترة">
                    <i class="bi bi-eye ms-1"></i>التفاصيل اليومية
                </button>
            `;
        }

        let shiftsBadgeHtml = `<span class="badge badge-shifts px-3 py-1 rounded-pill">${row.total_shift_units || 0} شفت</span>`;

        tbody.innerHTML += `
            <tr class="${trClass}">
                <td data-column="employee_code"><span class="badge badge-code font-monospace">${row.employee_code || "-"}</span></td>
                <td data-column="employee_name">${nameHtml}</td>
                <td data-column="department"><span class="badge badge-dept">${row.department || "-"}</span></td>
                <td data-column="job_title" class="text-secondary small">${row.job_title || "-"}</td>
                <td data-column="attendance_date">${row.attendance_date || "-"}</td>
                <td data-column="working_days_count"><span class="badge badge-days fw-bold px-2 py-1">${row.working_days_count || 0} يوم</span></td>
                <td data-column="shift_name"><span class="badge badge-dept">${row.shift_name || "-"}</span></td>
                <td data-column="shift_start_time">${row.shift_start_time || "-"}</td>
                <td data-column="shift_end_time">${row.shift_end_time || "-"}</td>
                <td data-column="check_in_time">${checkIn}</td>
                <td data-column="check_out_time">${checkOut}</td>
                <td data-column="working_hours" class="fw-bold text-white">${row.working_hours || 0}</td>
                <td data-column="overtime_hours" class="${overtimeClass}">${overtimeValue}</td>
                <td data-column="shift_deficit_hours">${row.shift_deficit_hours || 0}</td>
                <td data-column="late_minutes" class="${lateClass}">${lateValue}</td>
                <td data-column="status"><span class="badge ${statusBadgeClass}">${statusLabel}</span></td>
                <td data-column="worked_on_rest_day">${row.worked_on_rest_day ? '<i class="bi bi-check-circle-fill text-success"></i>' : '-'}</td>
                <td data-column="full_shift_count"><span class="badge badge-full-shift">${row.full_shift_count || 0}</span></td>
                <td data-column="half_shift_count"><span class="badge badge-half-shift">${row.half_shift_count || 0}</span></td>
                <td data-column="total_shift_units">${shiftsBadgeHtml}</td>
                <td data-column="shift_1_count">${row.shift_1_count || 0}</td>
                <td data-column="shift_2_count">${row.shift_2_count || 0}</td>
                <td data-column="worked_on_rest_days_count">${row.worked_on_rest_days_count || 0}</td>
                <td data-column="weekly_rest_days_count">${row.weekly_rest_days_count || 0}</td>
                <td data-column="absent_days_count"><span class="badge bg-danger bg-opacity-25 text-danger">${row.absent_days_count || 0}</span></td>
                <td data-column="actions">${actionsHtml}</td>
            </tr>
        `;
    });
    
    // Setup Modal buttons
    document.querySelectorAll(".btn-open-emp-modal").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const code = btn.dataset.code;
            openEmployeeModal(code);
        });
    });

    updateReportTableColumns();
}

function openEmployeeModal(employeeCode) {
    const summaryRow = currentReportData.find(r => r.row_kind === "summary" && String(r.employee_code) === String(employeeCode));
    const dailyRows = currentReportData.filter(r => r.row_kind !== "summary" && String(r.employee_code) === String(employeeCode));
    
    if (!summaryRow && dailyRows.length === 0) return;

    const empName = summaryRow ? summaryRow.employee_name : (dailyRows[0]?.employee_name || employeeCode);
    const empDept = summaryRow ? (summaryRow.department || "-") : (dailyRows[0]?.department || "-");
    
    document.getElementById("modalEmpName").innerText = empName;
    document.getElementById("modalEmpCode").innerText = employeeCode;
    document.getElementById("modalEmpDept").innerText = empDept;

    let periodDesc = "";
    if (currentPeriod === "custom") {
        const s = document.getElementById("reportStartDateInput")?.value || "";
        const e = document.getElementById("reportEndDateInput")?.value || "";
        periodDesc = `من ${s} إلى ${e}`;
    } else if (currentPeriod === "monthly") {
        periodDesc = `شهر ${document.getElementById("reportDateInput")?.value || ""}`;
    } else if (currentPeriod === "weekly") {
        periodDesc = `أسبوع ${document.getElementById("reportDateInput")?.value || ""}`;
    } else {
        periodDesc = `يوم ${document.getElementById("reportDateInput")?.value || ""}`;
    }
    document.getElementById("modalPeriodText").innerText = periodDesc;

    // Set Stats
    const totalDays = summaryRow ? (summaryRow.working_days_count || 0) : dailyRows.filter(r => r.status === "present" || r.status === "present_on_rest_day").length;
    const totalUnits = summaryRow ? (summaryRow.total_shift_units || 0) : 0;
    const totalFull = summaryRow ? (summaryRow.full_shift_count || 0) : 0;
    const totalHalf = summaryRow ? (summaryRow.half_shift_count || 0) : 0;
    const totalHours = summaryRow ? (summaryRow.working_hours || 0) : dailyRows.reduce((a, b) => a + (b.working_hours || 0), 0);
    const totalOt = summaryRow ? (summaryRow.total_overtime_hours ?? summaryRow.overtime_hours ?? 0) : dailyRows.reduce((a, b) => a + (b.overtime_hours || 0), 0);
    const totalLate = summaryRow ? (summaryRow.total_late_minutes ?? summaryRow.late_minutes ?? 0) : dailyRows.reduce((a, b) => a + (b.late_minutes || 0), 0);
    const totalAbsent = summaryRow ? (summaryRow.absent_days_count || 0) : dailyRows.filter(r => r.status === "absent").length;

    document.getElementById("modalStatDays").innerText = totalDays + " يوم";
    
    const shiftsCol = document.getElementById("modalStatShiftsCol");
    if (totalUnits > 0 || totalFull > 0 || totalHalf > 0) {
        shiftsCol.style.display = "";
        document.getElementById("modalStatShifts").innerHTML = `${totalUnits} شفت <br><small class="fw-normal text-muted" style="font-size:0.75rem;">(كامل: ${totalFull} | نصف: ${totalHalf})</small>`;
    } else {
        document.getElementById("modalStatShifts").innerText = totalUnits > 0 ? `${totalUnits}` : `${totalDays} يوم`;
    }
    
    document.getElementById("modalStatHours").innerText = Number(totalHours).toFixed(2) + " س";
    document.getElementById("modalStatOvertime").innerText = Number(totalOt).toFixed(2) + " س";
    document.getElementById("modalStatLate").innerText = totalLate + " دقيقة";
    document.getElementById("modalStatAbsent").innerText = totalAbsent + " يوم";

    // Populate daily records table
    const tbody = document.getElementById("modalDailyTableBody");
    tbody.innerHTML = "";

    if (dailyRows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-muted py-4">لا توجد تفاصيل يومية مسجلة لهذه الفترة</td></tr>`;
    } else {
        dailyRows.sort((a, b) => (a.attendance_date || "").localeCompare(b.attendance_date || ""));

        dailyRows.forEach(r => {
            let checkIn = "-";
            if (r.check_in_time) {
                const d = new Date(r.check_in_time);
                checkIn = isNaN(d.getTime()) ? r.check_in_time : d.toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
            }
            let checkOut = "-";
            if (r.check_out_time) {
                const d = new Date(r.check_out_time);
                checkOut = isNaN(d.getTime()) ? r.check_out_time : d.toLocaleTimeString("ar-EG", {hour: '2-digit', minute:'2-digit'});
            }

            let statusBadge = "bg-secondary";
            if (r.status === 'present') statusBadge = 'bg-success';
            else if (r.status === 'absent') statusBadge = 'bg-danger';
            else if (r.status === 'weekly_rest') statusBadge = 'bg-info text-dark';
            else if (r.status === 'present_on_rest_day') statusBadge = 'bg-warning text-dark';

            let lateClass = r.late_minutes > 0 ? "text-danger fw-bold" : "text-muted";
            let otClass = r.overtime_hours > 0 ? "text-success fw-bold" : "text-muted";
            let deficitClass = r.shift_deficit_hours > 0 ? "text-warning-emphasis fw-bold" : "text-muted";

            tbody.innerHTML += `
                <tr>
                    <td class="fw-bold text-white">${r.attendance_date || "-"}</td>
                    <td><span class="badge ${statusBadge}">${getReportStatusLabel(r.status)}</span></td>
                    <td><span class="badge badge-code font-monospace">${checkIn}</span></td>
                    <td><span class="badge badge-code font-monospace">${checkOut}</span></td>
                    <td><strong class="text-white">${r.shift_name || "-"}</strong></td>
                    <td class="fw-bold text-white">${r.working_hours || 0}</td>
                    <td class="${otClass}">${r.overtime_hours || 0}</td>
                    <td class="${deficitClass}">${r.shift_deficit_hours || 0}</td>
                    <td class="${lateClass}">${r.late_minutes ? r.late_minutes + ' د' : '0'}</td>
                </tr>
            `;
        });
    }

    // Setup Single Employee Export button
    const exportBtn = document.getElementById("modalExportSingleExcelBtn");
    if (exportBtn) {
        exportBtn.onclick = () => {
            let query = "";
            if (currentPeriod === "custom") {
                const s = document.getElementById("reportStartDateInput")?.value || "";
                const e = document.getElementById("reportEndDateInput")?.value || "";
                query = `/api/reports/range/export/excel?start_date=${s}&end_date=${e}${reportDepartmentQuery()}&view_mode=details&employee_code=${employeeCode}`;
            } else if (currentPeriod === "monthly") {
                const month = normalizeMonthInput(document.getElementById("reportDateInput")?.value || "");
                query = `/api/reports/monthly/export/excel?month=${month}${reportDepartmentQuery()}&view_mode=details&employee_code=${employeeCode}`;
            } else if (currentPeriod === "weekly") {
                const rawVal = document.getElementById("reportDateInput")?.value || "";
                query = `/api/reports/weekly/export/excel?report_date=${rawVal}${reportDepartmentQuery()}&employee_code=${employeeCode}`;
            } else {
                const rawVal = document.getElementById("reportDateInput")?.value || "";
                query = `/api/reports/daily/export/excel?report_date=${rawVal}${reportDepartmentQuery()}&employee_code=${employeeCode}`;
            }
            securedDownload(query);
        };
    }

    const modalEl = document.getElementById("employeeDetailsModal");
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}

async function renderReport(url) {
    try {
        const rows = await fetchJSON(url);
        currentReportData = rows;
        
        const hasSummary = rows.some(r => r.row_kind === "summary");
        currentViewMode = hasSummary ? "summary" : "daily";
        currentDetailedEmployeeCode = null;

        const titleSection = document.getElementById("reportTitleSection");
        if (titleSection) {
            const periodTitles = {
                custom: "نتائج التقرير المخصص (ملخص الموظفين)",
                daily: "نتائج التقرير اليومي",
                weekly: "نتائج التقرير الأسبوعي",
                monthly: "نتائج التقرير الشهري (ملخص الموظفين)"
            };
            titleSection.innerText = periodTitles[currentPeriod] || "نتائج التقرير";
        }

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
            link.download = fileNameMatch ? fileNameMatch[1] : "report.xlsx";
            link.click();
            window.URL.revokeObjectURL(url);
        })
        .catch((error) => showAlert("reportAlert", error.message));
}

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

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadDepartments();
    setupColumnVisibilityMenu();
    updateReportTableColumns();

    const todayObj = new Date();
    const today = todayObj.toISOString().split('T')[0];
    const firstDayOfMonth = new Date(todayObj.getFullYear(), todayObj.getMonth(), 1).toISOString().split('T')[0];
    const currentMonth = today.substring(0, 7);

    const startDateInput = document.getElementById("reportStartDateInput");
    const endDateInput = document.getElementById("reportEndDateInput");
    const dateInput = document.getElementById("reportDateInput");
    const dateLabel = document.getElementById("reportDateLabel");
    const rangeDatesWrapper = document.getElementById("rangeDatesWrapper");
    const singleDateWrapper = document.getElementById("singleDateWrapper");
    const searchBoxWrapper = document.getElementById("searchBoxWrapper");

    if (startDateInput) startDateInput.value = firstDayOfMonth;
    if (endDateInput) endDateInput.value = today;
    if (dateInput) dateInput.value = today;

    // Period toggle handler
    const periodRadios = document.querySelectorAll('input[name="reportPeriod"]');
    periodRadios.forEach(radio => {
        radio.addEventListener("change", (e) => {
            currentPeriod = e.target.value;
            if (currentPeriod === "custom") {
                if (rangeDatesWrapper) rangeDatesWrapper.style.display = "";
                if (singleDateWrapper) singleDateWrapper.style.display = "none";
                if (searchBoxWrapper) {
                    searchBoxWrapper.className = "col-lg-2 col-md-6";
                }
            } else if (currentPeriod === "monthly") {
                if (rangeDatesWrapper) rangeDatesWrapper.style.display = "none";
                if (singleDateWrapper) singleDateWrapper.style.display = "";
                if (dateLabel) dateLabel.textContent = "الشهر";
                if (dateInput) {
                    dateInput.type = "month";
                    dateInput.value = currentMonth;
                }
                if (searchBoxWrapper) {
                    searchBoxWrapper.className = "col-lg-3 col-md-6";
                }
            } else if (currentPeriod === "weekly") {
                if (rangeDatesWrapper) rangeDatesWrapper.style.display = "none";
                if (singleDateWrapper) singleDateWrapper.style.display = "";
                if (dateLabel) dateLabel.textContent = "تاريخ ضمن الأسبوع";
                if (dateInput) {
                    dateInput.type = "date";
                    dateInput.value = today;
                }
                if (searchBoxWrapper) {
                    searchBoxWrapper.className = "col-lg-3 col-md-6";
                }
            } else {
                // daily
                if (rangeDatesWrapper) rangeDatesWrapper.style.display = "none";
                if (singleDateWrapper) singleDateWrapper.style.display = "";
                if (dateLabel) dateLabel.textContent = "التاريخ اليومي";
                if (dateInput) {
                    dateInput.type = "date";
                    dateInput.value = today;
                }
                if (searchBoxWrapper) {
                    searchBoxWrapper.className = "col-lg-3 col-md-6";
                }
            }
        });
    });

    // Live search
    const searchBox = document.getElementById("reportSearchBox");
    if (searchBox) {
        searchBox.addEventListener("input", (e) => {
            filterTable(e.target.value);
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

    const btnBackToSummary = document.getElementById("btnBackToSummary");
    if (btnBackToSummary) {
        btnBackToSummary.addEventListener("click", () => {
            currentViewMode = "summary";
            currentDetailedEmployeeCode = null;
            const titleSection = document.getElementById("reportTitleSection");
            if (titleSection) {
                titleSection.innerHTML = `نتائج التقرير (ملخص الموظفين)`;
            }
            setupColumnVisibilityMenu();
            const searchTerm = searchBox ? searchBox.value : "";
            filterTable(searchTerm);
        });
    }

    // Unified Form Submit
    document.getElementById("unifiedReportForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();

        try {
            if (currentPeriod === "custom") {
                const s = startDateInput ? startDateInput.value : "";
                const e = endDateInput ? endDateInput.value : "";
                if (!s || !e) {
                    showAlert("reportAlert", "يرجى تحديد تاريخ البداية وتاريخ النهاية.");
                    return;
                }
                if (s > e) {
                    showAlert("reportAlert", "تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية.");
                    return;
                }
                await renderReport(`/api/reports/range?start_date=${s}&end_date=${e}${reportDepartmentQuery()}`);
            } else if (currentPeriod === "daily") {
                const rawVal = dateInput ? dateInput.value : "";
                if (!rawVal) return;
                await renderReport(`/api/reports/daily?report_date=${rawVal}${reportDepartmentQuery()}`);
            } else if (currentPeriod === "weekly") {
                const rawVal = dateInput ? dateInput.value : "";
                if (!rawVal) return;
                await renderReport(`/api/reports/weekly?report_date=${rawVal}${reportDepartmentQuery()}`);
            } else if (currentPeriod === "monthly") {
                const rawVal = dateInput ? dateInput.value : "";
                if (!rawVal) return;
                const month = normalizeMonthInput(rawVal);
                await renderReport(`/api/reports/monthly?month=${month}${reportDepartmentQuery()}`);
            }
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    // Excel Export Button
    document.getElementById("exportExcelBtn")?.addEventListener("click", () => {
        let query = "";
        if (currentPeriod === "custom") {
            const s = startDateInput ? startDateInput.value : "";
            const e = endDateInput ? endDateInput.value : "";
            if (!s || !e) {
                showAlert("reportAlert", "يرجى تحديد تاريخ البداية والنهاية أولاً.");
                return;
            }
            query = `/api/reports/range/export/excel?start_date=${s}&end_date=${e}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
            if (currentViewMode === "details" && currentDetailedEmployeeCode) {
                query += `&employee_code=${currentDetailedEmployeeCode}`;
            }
        } else if (currentPeriod === "daily") {
            const rawVal = dateInput ? dateInput.value : "";
            if (!rawVal) {
                showAlert("reportAlert", "يرجى اختيار التاريخ أولاً.");
                return;
            }
            query = `/api/reports/daily/export/excel?report_date=${rawVal}${reportDepartmentQuery()}`;
        } else if (currentPeriod === "weekly") {
            const rawVal = dateInput ? dateInput.value : "";
            if (!rawVal) {
                showAlert("reportAlert", "يرجى اختيار التاريخ أولاً.");
                return;
            }
            query = `/api/reports/weekly/export/excel?report_date=${rawVal}${reportDepartmentQuery()}`;
        } else if (currentPeriod === "monthly") {
            const rawVal = dateInput ? dateInput.value : "";
            if (!rawVal) {
                showAlert("reportAlert", "يرجى اختيار التاريخ أولاً.");
                return;
            }
            const month = normalizeMonthInput(rawVal);
            query = `/api/reports/monthly/export/excel?month=${month}${reportDepartmentQuery()}&view_mode=${currentViewMode}`;
            if (currentViewMode === "details" && currentDetailedEmployeeCode) {
                query += `&employee_code=${currentDetailedEmployeeCode}`;
            }
        }
        securedDownload(query);
    });
});
