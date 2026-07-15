
document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadMultiBranchStats();

    // Refresh stats every 30 seconds
    setInterval(loadMultiBranchStats, 30000);
});

const attendanceTypeLabels = {
    "check_in": "حضور",
    "check_out": "انصراف",
    "break_out": "خروج استراحة",
    "break_in": "عودة استراحة",
    "ot_in": "بداية دوام إضافي",
    "ot_out": "نهاية دوام إضافي",
    "0": "حضور",
    "1": "انصراف",
    "2": "خروج استراحة",
    "3": "عودة استراحة",
    "4": "بداية دوام إضافي",
    "5": "نهاية دوام إضافي",
};

async function loadMultiBranchStats() {
    try {
        const allStats = await fetchJSON("/api/branches/all/stats");
        
        // Calculate total summary
        let totalEmployees = 0;
        let totalAttendanceToday = 0;
        let totalLogsToday = 0;
        let totalOnlineDevices = 0;
        let allLatestLogs = [];
        
        allStats.forEach(branchStats => {
            totalEmployees += branchStats.total_employees;
            totalAttendanceToday += branchStats.attendance_today;
            totalLogsToday += branchStats.logs_today;
            totalOnlineDevices += branchStats.online_devices;
            allLatestLogs.push(...branchStats.latest_logs.map(log => ({
                ...log,
                branch_name: branchStats.name
            })));
        });
        
        // Update summary cards
        document.getElementById("allTotalEmployees").textContent = totalEmployees;
        document.getElementById("allAttendanceToday").textContent = totalAttendanceToday;
        document.getElementById("allLogsToday").textContent = totalLogsToday;
        document.getElementById("allOnlineDevices").textContent = totalOnlineDevices;
        
        // Update branches grid
        const branchesGrid = document.getElementById("branchesGrid");
        branchesGrid.innerHTML = allStats.map(branchStats => `
            <div class="col-xl-4 col-md-6">
                <div class="card panel-card p-4 h-100">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="fw-bold mb-0">${branchStats.name}</h5>
                        <a href="/branches/${branchStats.id}" class="btn btn-sm btn-primary">عرض</a>
                    </div>
                    <div class="row g-2 mb-3">
                        <div class="col-6">
                            <div class="small text-muted">موظفين</div>
                            <div class="fw-bold">${branchStats.total_employees}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">حاضرين</div>
                            <div class="fw-bold text-success">${branchStats.attendance_today}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">سجلات اليوم</div>
                            <div class="fw-bold">${branchStats.logs_today}</div>
                        </div>
                        <div class="col-6">
                            <div class="small text-muted">أجهزة متصلة</div>
                            <div class="fw-bold">${branchStats.online_devices} / ${branchStats.total_devices}</div>
                        </div>
                    </div>
                    ${branchStats.inactive_devices.length > 0 ? `
                        <div class="small text-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            ${branchStats.inactive_devices.length} أجهزة منقطعة
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
        // Update all latest logs
        const allLatestLogsBody = document.getElementById("allLatestLogsBody");
        // Sort logs by check_time descending
        allLatestLogs.sort((a, b) => new Date(b.check_time) - new Date(a.check_time));
        allLatestLogsBody.innerHTML = allLatestLogs.slice(0, 20).map(log => `
            <tr>
                <td>${log.branch_name}</td>
                <td>${log.employee_code}</td>
                <td>${log.employee_name || "-"}</td>
                <td>${log.device_name || "-"}</td>
                <td>${new Date(log.check_time).toLocaleString("ar-EG")}</td>
                <td>${attendanceTypeLabels[log.attendance_type] || log.attendance_type || "-"}</td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error(error);
    }
}
