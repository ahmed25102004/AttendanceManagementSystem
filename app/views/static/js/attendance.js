let allLogs = [];
let currentDateFrom = "";
let currentDateTo = "";

function getDayName(date) {
    const days = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
    return days[date.getDay()];
}

function normalizeAttendanceType(type) {
    const map = {
        "0": "check_in",
        "1": "check_out",
        "4": "ot_in",
        "5": "ot_out",
    };
    return map[type] || type;
}

function getDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function formatDisplayTime(dateValue) {
    if (!dateValue) return "-";
    return new Date(dateValue).toLocaleTimeString("ar-EG", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatDisplayDate(dateValue) {
    if (!dateValue) return "-";
    const [year, month, day] = dateValue.split("-");
    return `${day}/${month}/${year}`;
}

function buildAttendanceSummaries(logs) {
    const summaries = new Map();

    logs.forEach((log) => {
        const checkDate = new Date(log.check_time);
        const dateKey = getDateKey(checkDate);
        const employeeKey = log.employee_id || `code-${log.employee_code}`;
        const summaryKey = `${log.branch_id || "no-branch"}-${employeeKey}-${dateKey}`;
        const normalizedType = normalizeAttendanceType(log.attendance_type);

        if (!summaries.has(summaryKey)) {
            summaries.set(summaryKey, {
                key: summaryKey,
                branch_id: log.branch_id,
                branch_name: log.branch_name || "-",
                date_key: dateKey,
                day_name: getDayName(checkDate),
                employee_id: log.employee_id || null,
                employee_name: log.employee_name || "Unknown",
                employee_code: log.employee_code || "-",
                check_in_time: null,
                check_out_time: null,
                ot_in_time: null,
                ot_out_time: null,
                device_names: new Set(),
                verify_types: new Set(),
                sources: new Set(),
                latest_event_time: checkDate,
            });
        }

        const summary = summaries.get(summaryKey);
        const logTime = new Date(log.check_time);

        if (log.device_name) {
            summary.device_names.add(log.device_name);
        }
        if (log.verify_type) {
            summary.verify_types.add(getVerifyTypeName(log.verify_type));
        }
        if (log.source) {
            summary.sources.add(log.source);
        }
        if (logTime > summary.latest_event_time) {
            summary.latest_event_time = logTime;
        }

        if (normalizedType === "check_in") {
            if (!summary.check_in_time || logTime < new Date(summary.check_in_time)) {
                summary.check_in_time = log.check_time;
            }
        }

        if (normalizedType === "check_out") {
            if (!summary.check_out_time || logTime > new Date(summary.check_out_time)) {
                summary.check_out_time = log.check_time;
            }
        }

        if (normalizedType === "ot_in") {
            if (!summary.ot_in_time || logTime < new Date(summary.ot_in_time)) {
                summary.ot_in_time = log.check_time;
            }
        }

        if (normalizedType === "ot_out") {
            if (!summary.ot_out_time || logTime > new Date(summary.ot_out_time)) {
                summary.ot_out_time = log.check_time;
            }
        }
    });

    return Array.from(summaries.values()).sort((a, b) => b.latest_event_time - a.latest_event_time);
}

async function loadAttendanceLogs() {
    allLogs = await fetchJSON("/api/attendance-logs"); // No all=true, let backend filter by current branch
    // Sort logs by check_time descending (newest at top)
    allLogs.sort((a, b) => new Date(b.check_time) - new Date(a.check_time));
    renderAttendanceLogs();
}

function renderAttendanceLogs() {
    const tbody = document.getElementById("attendanceLogTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    // Filter logs
    let filteredLogs = [...allLogs];
    
    // Auto-filter by current branch id (just for redundancy, backend already filters)
    const currentBranchId = getCurrentBranchId();
    if (currentBranchId) {
        filteredLogs = filteredLogs.filter(log => log.branch_id === Number(currentBranchId));
    }
    
    // Date from filter
    if (currentDateFrom) {
        const fromDate = new Date(`${currentDateFrom}T00:00:00`);
        fromDate.setHours(0, 0, 0, 0);
        filteredLogs = filteredLogs.filter(log => new Date(log.check_time) >= fromDate);
    }
    
    // Date to filter
    if (currentDateTo) {
        const toDate = new Date(`${currentDateTo}T23:59:59`);
        toDate.setHours(23, 59, 59, 999);
        filteredLogs = filteredLogs.filter(log => new Date(log.check_time) <= toDate);
    }

    const summaries = buildAttendanceSummaries(filteredLogs);
    summaries.forEach((summary) => {
        addAttendanceSummaryRow(summary);
    });
}

function setToday() {
    const today = new Date();
    const dateStr = getDateKey(today);
    document.getElementById("dateFrom").value = dateStr;
    document.getElementById("dateTo").value = dateStr;
    currentDateFrom = dateStr;
    currentDateTo = dateStr;
    renderAttendanceLogs();
}

function setThisWeek() {
    const today = new Date();
    const dayOfWeek = today.getDay(); // 0 is Sunday
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - dayOfWeek);
    startOfWeek.setHours(0, 0, 0, 0);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    endOfWeek.setHours(23, 59, 59, 999);
    
    document.getElementById("dateFrom").value = getDateKey(startOfWeek);
    document.getElementById("dateTo").value = getDateKey(endOfWeek);
    currentDateFrom = getDateKey(startOfWeek);
    currentDateTo = getDateKey(endOfWeek);
    renderAttendanceLogs();
}

function setThisMonth() {
    const today = new Date();
    const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59, 999);
    
    document.getElementById("dateFrom").value = getDateKey(startOfMonth);
    document.getElementById("dateTo").value = getDateKey(endOfMonth);
    currentDateFrom = getDateKey(startOfMonth);
    currentDateTo = getDateKey(endOfMonth);
    renderAttendanceLogs();
}

function getAttendanceTypeName(type) {
    const map = {
        'check_in': 'حضور',
        'check_out': 'انصراف',
        'break_out': 'خروج استراحة',
        'break_in': 'عودة استراحة',
        'ot_in': 'بداية دوام إضافي',
        'ot_out': 'نهاية دوام إضافي',
        '0': 'حضور',
        '1': 'انصراف',
        '2': 'خروج استراحة',
        '3': 'عودة استراحة',
        '4': 'بداية دوام إضافي',
        '5': 'نهاية دوام إضافي',
    };
    return map[type] || type;
}

function getAttendanceTypeBadge(type) {
    const map = {
        'check_in': 'bg-primary',
        'check_out': 'bg-danger',
        'break_out': 'bg-warning',
        'break_in': 'bg-info',
        'ot_in': 'bg-success',
        'ot_out': 'bg-secondary',
        '0': 'bg-primary',
        '1': 'bg-danger',
        '2': 'bg-warning',
        '3': 'bg-info',
        '4': 'bg-success',
        '5': 'bg-secondary',
    };
    return map[type] || 'bg-secondary';
}

function getVerifyTypeName(type) {
    const map = {
        'fingerprint': 'بصمة',
        'card': 'بطاقة',
        'face': 'وجه',
        'password': 'كلمة مرور',
        '0': 'كلمة مرور',
        '1': 'بصمة',
        '2': 'بطاقة',
        '15': 'وجه',
    };
    return map[type] || type;
}

function addAttendanceSummaryRow(summary) {
    const tbody = document.getElementById("attendanceLogTableBody");
    if (!tbody) return;

    const row = document.createElement("tr");
    row.id = `summary-${summary.key}`;
    const employeeCell = summary.employee_id
        ? `<a href="/employees/${summary.employee_id}" class="text-decoration-none fw-semibold">${summary.employee_name}</a>`
        : summary.employee_name;
    const verifyTypes = Array.from(summary.verify_types);
    const devices = Array.from(summary.device_names);
    const sources = Array.from(summary.sources);

    row.innerHTML = `
        <td>${summary.day_name}</td>
        <td>${formatDisplayDate(summary.date_key)}</td>
        <td>${employeeCell}</td>
        <td>${summary.employee_code}</td>
        <td>${formatDisplayTime(summary.check_in_time)}</td>
        <td>${formatDisplayTime(summary.check_out_time)}</td>
        <td>${formatDisplayTime(summary.ot_in_time)}</td>
        <td>${formatDisplayTime(summary.ot_out_time)}</td>
        <td>${verifyTypes.length ? verifyTypes.join(" / ") : "-"}</td>
        <td>${devices.length ? devices.join(" / ") : "-"}</td>
        <td>${sources.length ? sources.join(" / ") : "-"}</td>
    `;
    tbody.appendChild(row);
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    try {
        await loadAttendanceLogs();
        
        // Check if we have WebSocket initialized
        if (!window.ws) {
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            window.ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/attendance`);
            
            window.ws.onopen = () => {
                console.log("Attendance page WS connected");
                const statusEl = document.getElementById("attendanceLogStatus");
                if (statusEl) {
                    statusEl.textContent = "متصل ✓";
                    statusEl.className = "text-success small";
                }
            };
            
            window.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === "attendance_log") {
                        const alreadyExists = allLogs.some((log) => log.id === message.data.id);
                        if (!alreadyExists) {
                            allLogs.unshift(message.data);
                        }
                        renderAttendanceLogs();
                        // Show notification
                        showAlert("attendanceAlert", `✅ ${message.data.employee_name} ${getAttendanceTypeName(message.data.attendance_type)} في ${new Date(message.data.check_time).toLocaleTimeString("ar-EG")}`, "success");
                    }
                } catch (error) {
                    console.error("Error parsing WS message:", error);
                }
            };
            
            window.ws.onclose = () => {
                console.log("WS closed, reconnecting in 3s");
                const statusEl = document.getElementById("attendanceLogStatus");
                if (statusEl) {
                    statusEl.textContent = "غير متصل, جارِ إعادة الاتصال...";
                    statusEl.className = "text-warning small";
                }
                setTimeout(() => window.location.reload(), 3000);
            };
        }
    } catch (error) {
        showAlert("attendanceAlert", error.message);
    }

    document.getElementById("dateFrom").addEventListener("change", (event) => {
        currentDateFrom = event.target.value;
        renderAttendanceLogs();
    });
    
    document.getElementById("dateTo").addEventListener("change", (event) => {
        currentDateTo = event.target.value;
        renderAttendanceLogs();
    });
    
    document.getElementById("btnToday").addEventListener("click", setToday);
    document.getElementById("btnThisWeek").addEventListener("click", setThisWeek);
    document.getElementById("btnThisMonth").addEventListener("click", setThisMonth);
});
