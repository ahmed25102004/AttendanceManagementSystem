const seenLogIds = new Set();

async function loadAttendanceEmployees() {
    const employees = await fetchJSON("/api/employees?all=true");
    const checkInSelect = document.getElementById("attendance_employee_id");
    const checkOutSelect = document.getElementById("checkout_employee_id");
    if (!checkInSelect || !checkOutSelect) return;
    checkInSelect.innerHTML = '<option value="">اختر الموظف</option>';
    checkOutSelect.innerHTML = '<option value="">اختر الموظف</option>';
    employees.forEach((employee) => {
        const displayName = employee.full_name || [employee.first_name, employee.last_name].filter(Boolean).join(" ").trim();
        const option = `<option value="${employee.id}">${displayName}</option>`;
        checkInSelect.innerHTML += option;
        checkOutSelect.innerHTML += option;
    });
}

async function loadAttendanceRecords(dateValue = "") {
    let query = "?all=true";
    if (dateValue) {
        query += `&attendance_date=${dateValue}`;
    }
    const records = await fetchJSON(`/api/attendance${query}`);
    const tbody = document.getElementById("attendanceTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    records.forEach((record) => {
        tbody.innerHTML += `
            <tr>
                <td>${record.employee_name}</td>
                <td>${record.attendance_date}</td>
                <td>${record.check_in_time ? new Date(record.check_in_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${record.check_out_time ? new Date(record.check_out_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${record.working_hours}</td>
                <td><span class="badge text-bg-${record.is_late ? "warning" : "success"}">${record.is_late ? "متأخر" : "في الموعد"}</span></td>
                <td>${record.source_type === "manual" ? "يدوي" : record.source_type}</td>
            </tr>
        `;
    });
}

async function loadAttendanceLogs() {
    const logs = await fetchJSON("/api/attendance-logs?all=true");
    const tbody = document.getElementById("attendanceLogTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    seenLogIds.clear();

    // Sort logs by check_time descending (newest at top)
    logs.sort((a, b) => new Date(b.check_time) - new Date(a.check_time));
    
    logs.forEach((log) => {
        addAttendanceLogToTable(log, false);
    });
}

function addAttendanceLogToTable(log, prepend = true) {
    if (seenLogIds.has(log.id)) {
        return; // Avoid duplicates
    }
    seenLogIds.add(log.id);
    const tbody = document.getElementById("attendanceLogTableBody");
    if (!tbody) return;

    // Format log for display
    const employeeName = log.employee_name || "Unknown";
    const checkTime = new Date(log.check_time).toLocaleString("ar-EG");

    const row = document.createElement("tr");
    row.id = `log-${log.id}`;
    row.innerHTML = `
        <td>${checkTime}</td>
        <td>${employeeName}</td>
        <td>${log.employee_code}</td>
        <td><span class="badge text-bg-primary">${log.attendance_type}</span></td>
        <td><span class="badge text-bg-secondary">${log.verify_type}</span></td>
        <td>${log.device_name}</td>
        <td><span class="badge text-bg-info">${log.source}</span></td>
    `;

    if (prepend) {
        tbody.insertBefore(row, tbody.firstChild);
        // Add a little animation
        row.style.backgroundColor = "#d1fae5";
        setTimeout(() => {
            row.style.transition = "background-color 0.5s";
            row.style.backgroundColor = "";
        }, 1000);
    } else {
        tbody.appendChild(row);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    try {
        await loadAttendanceEmployees();
        await loadAttendanceRecords();
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
                        addAttendanceLogToTable(message.data, true);
                        // Show notification
                        showAlert("attendanceAlert", `✅ ${message.data.employee_name} ${message.data.attendance_type} في ${new Date(message.data.check_time).toLocaleTimeString("ar-EG")}`, "success");
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

    document.getElementById("attendanceFilterDate").addEventListener("change", async (event) => {
        await loadAttendanceRecords(event.target.value);
    });

    document.getElementById("checkInForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await fetchJSON("/api/attendance/check-in", {
                method: "POST",
                body: JSON.stringify({
                    employee_id: Number(document.getElementById("attendance_employee_id").value),
                    attendance_date: document.getElementById("attendance_date").value || null,
                    source_type: "manual",
                    verification_data: { note: "تم تسجيل الحضور بواسطة المدير" },
                }),
            });
            await loadAttendanceRecords(document.getElementById("attendanceFilterDate").value);
            showAlert("attendanceAlert", "تم تسجيل الحضور بنجاح.", "success");
        } catch (error) {
            showAlert("attendanceAlert", error.message);
        }
    });

    document.getElementById("checkOutForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await fetchJSON("/api/attendance/check-out", {
                method: "POST",
                body: JSON.stringify({
                    employee_id: Number(document.getElementById("checkout_employee_id").value),
                    attendance_date: document.getElementById("checkout_date").value || null,
                }),
            });
            await loadAttendanceRecords(document.getElementById("attendanceFilterDate").value);
            showAlert("attendanceAlert", "تم تسجيل الانصراف بنجاح.", "success");
        } catch (error) {
            showAlert("attendanceAlert", error.message);
        }
    });
});
