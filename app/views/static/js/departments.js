
const departmentCache = new Map();

function getPolicyDisplayName(policy) {
    if (policy === "leather_department") {
        return "قسم الجلدية";
    }
    if (policy === "reception_department") {
        return "قسم الريسبشن";
    }
    if (policy === "workers_department") {
        return "قسم العمال";
    }
    if (policy === "doctors_department") {
        return "الدكاتره";
    }
    if (policy === "call_center_department") {
        return "قسم الكول سنتر";
    }
    return "سياسة افتراضية";
}

function toggleUnifiedSettings() {
    const policy = el("departmentAttendancePolicy").value;
    const unifiedSettings = document.getElementById("unifiedSettings");
    const callCenterSettings = document.getElementById("callCenterSettings");
    const workersSettings = document.getElementById("workersSettingsSection");
    
    if (unifiedSettings) {
        unifiedSettings.style.display = 
            (policy === "reception_department" || policy === "doctors_department") ? "block" : "none";
    }
    if (callCenterSettings) {
        callCenterSettings.style.display = policy === "call_center_department" ? "block" : "none";
    }
    if (workersSettings) {
        workersSettings.style.display = policy === "workers_department" ? "block" : "none";
    }
}

function formatTimeForInput(timeStr) {
    if (!timeStr) return "08:00";
    // Takes "08:00:00" and returns "08:00"
    if (typeof timeStr === "string") {
        return timeStr.substring(0, 5);
    }
    return timeStr;
}

function showDepartmentAlert(message, type = "danger") {
    const element = document.getElementById("departmentAlert");
    if (!element) return;
    element.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    setTimeout(() => {
        element.innerHTML = "";
    }, 3000);
}

async function loadDepartments() {
    const departments = await fetchJSON("/api/departments");
    const tbody = document.getElementById("departmentTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    departmentCache.clear();

    departments.forEach((department) => {
        departmentCache.set(department.id, department);
        tbody.innerHTML += `
            <tr>
                <td>${department.name}</td>
                <td>${getPolicyDisplayName(department.attendance_policy)}</td>
                <td>${department.description || "-"}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="editDepartment(${department.id})">تعديل</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDepartment(${department.id})">حذف</button>
                </td>
            </tr>
        `;
    });
}

function resetDepartmentForm() {
    const form = document.getElementById("departmentForm");
    if (form) form.reset();
    el("departmentId").value = "";
    el("overtimeEnabled").checked = true;
    el("overtimeStartTime").disabled = false;
    toggleUnifiedSettings();
}

function editDepartment(departmentId) {
    const department = departmentCache.get(departmentId);
    if (!department) {
        showDepartmentAlert("تعذر تحميل بيانات القسم.");
        return;
    }

    el("departmentId").value = department.id;
    el("departmentName").value = department.name;
    el("departmentAttendancePolicy").value = department.attendance_policy || "default";
    el("departmentDescription").value = department.description || "";
    
    // Set shift settings
    el("shiftStartTime").value = formatTimeForInput(department.shift_start_time || department.half_shift_start_time);
    el("shiftEndTime").value = formatTimeForInput(department.shift_end_time || department.half_shift_end_time);
    el("shiftHours").value = department.shift_hours || department.half_shift_hours;
    el("lateStartTime").value = formatTimeForInput(department.late_start_time || department.half_shift_start_time);
    el("attendanceEndTime").value = formatTimeForInput(department.attendance_end_time);
    el("overtimeStartTime").value = formatTimeForInput(department.overtime_start_time);
    el("overtimeEnabled").checked = department.overtime_enabled !== false;
    el("overtimeStartTime").disabled = !(department.overtime_enabled !== false);
    
    // Set evening shift settings
    const hasEveningShift = !!(department.evening_shift_start_time || department.evening_shift_end_time);
    el("enableEveningShift").checked = hasEveningShift;
    el("eveningShiftSettings").style.display = hasEveningShift ? "block" : "none";
    el("eveningShiftStartTime").value = formatTimeForInput(department.evening_shift_start_time);
    el("eveningShiftEndTime").value = formatTimeForInput(department.evening_shift_end_time);
    el("eveningShiftHours").value = department.evening_shift_hours || "";
    el("eveningShiftLateStartTime").value = formatTimeForInput(department.evening_shift_late_start_time);
    
    // Set legacy fields (for backward compatibility)
    el("halfShiftStartTime").value = formatTimeForInput(department.shift_start_time || department.half_shift_start_time);
    el("halfShiftEndTime").value = formatTimeForInput(department.shift_end_time || department.half_shift_end_time);
    el("halfShiftHours").value = department.shift_hours || department.half_shift_hours;
    el("fullShiftStartTime").value = formatTimeForInput(department.shift_start_time || department.half_shift_start_time);
    el("fullShiftEndTime").value = formatTimeForInput(department.shift_end_time || department.full_shift_end_time);
    el("fullShiftHours").value = department.shift_hours || department.half_shift_hours;
    el("gracePeriodMinutes").value = 30;

    const callCenterShift1Start = document.getElementById("editCallCenterShift1StartTime");
    if (callCenterShift1Start) {
        callCenterShift1Start.value = formatTimeForInput(department.shift_start_time);
        el("editCallCenterShift1GraceEndTime").value = formatTimeForInput(department.late_start_time);
        el("editCallCenterShift1EndTime").value = formatTimeForInput(department.shift_end_time);
        el("editCallCenterShift2StartTime").value = formatTimeForInput(department.evening_shift_start_time);
        el("editCallCenterShift2GraceEndTime").value = formatTimeForInput(department.evening_shift_late_start_time);
        el("editCallCenterShift2EndTime").value = formatTimeForInput(department.evening_shift_end_time);
    }
    
    const workersShift1Start = document.getElementById("editWorkersShift1StartTime");
    if (workersShift1Start) {
        workersShift1Start.value = formatTimeForInput(department.shift_start_time);
        el("editWorkersShift1GraceEndTime").value = formatTimeForInput(department.late_start_time);
        el("editWorkersShift1EndTime").value = formatTimeForInput(department.shift_end_time);
        el("editWorkersShift2StartTime").value = formatTimeForInput(department.evening_shift_start_time);
        el("editWorkersShift2GraceEndTime").value = formatTimeForInput(department.evening_shift_late_start_time);
        el("editWorkersShift2EndTime").value = formatTimeForInput(department.evening_shift_end_time);
    }
    
    toggleUnifiedSettings();
}

async function deleteDepartment(departmentId) {
    if (!confirm("هل تريد حذف هذا القسم؟")) {
        return;
    }

    try {
        await fetchJSON(`/api/departments/${departmentId}`, { method: "DELETE" });
        await loadDepartments();
        resetDepartmentForm();
        showDepartmentAlert("تم حذف القسم بنجاح.", "success");
    } catch (error) {
        showDepartmentAlert(error.message);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const user = await hydrateUser();

    try {
        await loadDepartments();
    } catch (error) {
        showDepartmentAlert(error.message);
    }
    
    // Add listener for policy change to toggle settings
    const policySelect = el("departmentAttendancePolicy");
    if (policySelect) {
        policySelect.addEventListener("change", toggleUnifiedSettings);
    }
    
    // Add listener for overtime toggle
    const overtimeToggle = el("overtimeEnabled");
    if (overtimeToggle) {
        overtimeToggle.addEventListener("change", (e) => {
            el("overtimeStartTime").disabled = !e.target.checked;
        });
    }
    
    // Add listener for evening shift toggle
    const eveningShiftToggle = el("enableEveningShift");
    if (eveningShiftToggle) {
        eveningShiftToggle.addEventListener("change", (e) => {
            el("eveningShiftSettings").style.display = e.target.checked ? "block" : "none";
        });
    }

    const form = document.getElementById("departmentForm");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const departmentId = el("departmentId").value;
            const policy = el("departmentAttendancePolicy").value;

            const payload = {
                name: el("departmentName").value.trim(),
                attendance_policy: policy,
                description: el("departmentDescription").value.trim() || null,
            };
            
            if (policy === "reception_department" || policy === "doctors_department") {
                // Unified fields
                payload.shift_start_time = el("shiftStartTime").value + ":00";
                payload.shift_end_time = el("shiftEndTime").value + ":00";
                payload.shift_hours = parseInt(el("shiftHours").value);
                payload.late_start_time = el("lateStartTime").value + ":00";
                payload.attendance_end_time = el("attendanceEndTime").value + ":00";
                payload.overtime_enabled = el("overtimeEnabled").checked;
                payload.overtime_start_time = el("overtimeStartTime").value + ":00";
                
                // Evening shift settings
                const eveningShiftEnabled = el("enableEveningShift").checked;
                if (eveningShiftEnabled) {
                    payload.evening_shift_start_time = el("eveningShiftStartTime").value ? el("eveningShiftStartTime").value + ":00" : null;
                    payload.evening_shift_end_time = el("eveningShiftEndTime").value ? el("eveningShiftEndTime").value + ":00" : null;
                    payload.evening_shift_hours = el("eveningShiftHours").value ? parseInt(el("eveningShiftHours").value) : null;
                    payload.evening_shift_late_start_time = el("eveningShiftLateStartTime").value ? el("eveningShiftLateStartTime").value + ":00" : null;
                } else {
                    payload.evening_shift_start_time = null;
                    payload.evening_shift_end_time = null;
                    payload.evening_shift_hours = null;
                    payload.evening_shift_late_start_time = null;
                }
                
                // Legacy fields (for backward compatibility)
                payload.half_shift_start_time = el("shiftStartTime").value + ":00";
                payload.half_shift_end_time = el("shiftEndTime").value + ":00";
                payload.half_shift_hours = parseInt(el("shiftHours").value);
                payload.full_shift_start_time = el("shiftStartTime").value + ":00";
                payload.full_shift_end_time = el("shiftEndTime").value + ":00";
                payload.full_shift_hours = parseInt(el("shiftHours").value);
                payload.grace_period_minutes = 30;
            }
            
            if (policy === "call_center_department") {
                const shift1Start = el("editCallCenterShift1StartTime").value;
                const shift1GraceEnd = el("editCallCenterShift1GraceEndTime").value;
                const shift1End = el("editCallCenterShift1EndTime").value;
                const shift2Start = el("editCallCenterShift2StartTime").value;
                const shift2GraceEnd = el("editCallCenterShift2GraceEndTime").value;
                const shift2End = el("editCallCenterShift2EndTime").value;
                
                if (!shift1Start || !shift1GraceEnd || !shift1End || !shift2Start || !shift2GraceEnd || !shift2End) {
                    showDepartmentAlert("يرجى إدخال جميع مواعيد الشيفت الأول والثاني لقسم الكول سنتر.");
                    return;
                }
                
                payload.shift_start_time = shift1Start + ":00";
                payload.late_start_time = shift1GraceEnd + ":00";
                payload.shift_end_time = shift1End + ":00";
                payload.evening_shift_start_time = shift2Start + ":00";
                payload.evening_shift_late_start_time = shift2GraceEnd + ":00";
                payload.evening_shift_end_time = shift2End + ":00";
                payload.evening_shift_hours = null;
            }
            
            if (policy === "workers_department") {
                const shift1Start = el("editWorkersShift1StartTime").value;
                const shift1GraceEnd = el("editWorkersShift1GraceEndTime").value;
                const shift1End = el("editWorkersShift1EndTime").value;
                const shift2Start = el("editWorkersShift2StartTime").value;
                const shift2GraceEnd = el("editWorkersShift2GraceEndTime").value;
                const shift2End = el("editWorkersShift2EndTime").value;
                
                if (!shift1Start || !shift1GraceEnd || !shift1End || !shift2Start || !shift2GraceEnd || !shift2End) {
                    showDepartmentAlert("يرجى إدخال جميع مواعيد الشيفت الأول والثاني لقسم العمال.");
                    return;
                }
                
                payload.shift_start_time = shift1Start + ":00";
                payload.late_start_time = shift1GraceEnd + ":00";
                payload.shift_end_time = shift1End + ":00";
                payload.evening_shift_start_time = shift2Start + ":00";
                payload.evening_shift_late_start_time = shift2GraceEnd + ":00";
                payload.evening_shift_end_time = shift2End + ":00";
                payload.evening_shift_hours = null;
            }

            const method = departmentId ? "PUT" : "POST";
            const url = departmentId ? `/api/departments/${departmentId}` : "/api/departments";

            try {
                await fetchJSON(url, {
                    method,
                    body: JSON.stringify(payload),
                });
                resetDepartmentForm();
                await loadDepartments();
                showDepartmentAlert(departmentId ? "تم تحديث بيانات القسم بنجاح." : "تم إضافة القسم بنجاح.", "success");
            } catch (error) {
                showDepartmentAlert(error.message);
            }
        });
    }
});
