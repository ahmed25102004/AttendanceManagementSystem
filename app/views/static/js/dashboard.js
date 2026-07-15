let attendanceLineChart = null;
const attendanceTypeMap = {
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
    "5": "نهاية دوام إضافي"
};
const attendanceTypeBadgeMap = {
    "check_in": "bg-primary",
    "check_out": "bg-danger",
    "break_out": "bg-warning",
    "break_in": "bg-info",
    "ot_in": "bg-success",
    "ot_out": "bg-secondary",
    "0": "bg-primary",
    "1": "bg-danger",
    "2": "bg-warning",
    "3": "bg-info",
    "4": "bg-success",
    "5": "bg-secondary"
};

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();

    try {
        // Load all data in parallel
        const [kpis, summary, branches, alerts, recentLogs] = await Promise.all([
            fetchJSON("/api/dashboard/kpis"),
            fetchJSON("/api/dashboard/summary"),
            fetchJSON("/api/dashboard/branches-stats"),
            fetchJSON("/api/dashboard/alerts"),
            fetchJSON("/api/dashboard/recent-logs")
        ]);
        
        // Render KPIs
        renderKpis(kpis);
        document.getElementById("absentToday").textContent = kpis.absent_today;
        
        // Render charts
        renderLineChart(summary);
        
        // Render branches
        renderBranches(branches);
        
        // Render alerts
        renderAlerts(alerts);
        
        // Render recent logs
        renderRecentLogs(recentLogs);
        
        // Auto-refresh every 30 seconds
        setInterval(async () => {
            try {
                const [updatedKpis, updatedAlerts, updatedRecentLogs] = await Promise.all([
                    fetchJSON("/api/dashboard/kpis"),
                    fetchJSON("/api/dashboard/alerts"),
                    fetchJSON("/api/dashboard/recent-logs")
                ]);
                
                renderKpis(updatedKpis);
                document.getElementById("absentToday").textContent = updatedKpis.absent_today;
                renderAlerts(updatedAlerts);
                renderRecentLogs(updatedRecentLogs);
            } catch (err) {
                console.error(err);
            }
        }, 30000);
        
    } catch (error) {
        showAlert("dashboardAlert", error.message);
    }
});

function renderKpis(kpis) {
  const totalEmployeesEl = document.getElementById("totalEmployees");
  if (totalEmployeesEl) totalEmployeesEl.textContent = kpis.total_employees || 0;
  const presentTodayEl = document.getElementById("presentToday");
  if (presentTodayEl) presentTodayEl.textContent = kpis.present_today || 0;
  const currentlyWorkingEl = document.getElementById("currentlyWorking");
  if (currentlyWorkingEl) currentlyWorkingEl.textContent = kpis.currently_working || 0;
  const onlineDevicesEl = document.getElementById("onlineDevices");
  if (onlineDevicesEl) onlineDevicesEl.textContent = kpis.online_devices || 0;
  const totalDevicesEl = document.getElementById("totalDevices");
  if (totalDevicesEl) totalDevicesEl.textContent = kpis.total_devices || 0;
  const absentTodayEl = document.getElementById("absentToday");
  if (absentTodayEl) absentTodayEl.textContent = kpis.absent_today || 0;
}

function renderLineChart(summary) {
    const lineCtx = document.getElementById("attendanceChart").getContext("2d");
    if (attendanceLineChart) {
        attendanceLineChart.destroy();
    }
    
    attendanceLineChart = new Chart(lineCtx, {
        type: "line",
        data: {
            labels: summary.weekly_data.labels,
            datasets: [
                {
                    label: "الحاضرون",
                    data: summary.weekly_data.present,
                    borderColor: "#0d6efd",
                    backgroundColor: "rgba(13, 110, 253, 0.1)",
                    fill: true,
                    tension: 0.4
                },
                {
                    label: "المتأخرون",
                    data: summary.weekly_data.late,
                    borderColor: "#ffc107",
                    backgroundColor: "rgba(255, 193, 7, 0.1)",
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "top"
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderBranches(branches) {
    const tbody = document.getElementById("branchesTableBody");
    tbody.innerHTML = branches.map(branch => `
        <tr>
            <td><a href="/branches/${branch.id}" class="fw-medium text-decoration-none">${branch.name}</a></td>
            <td>${branch.total_employees}</td>
            <td>${branch.present_today}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="height: 8px;">
                        <div class="progress-bar" style="width: ${Math.min(branch.attendance_rate, 100)}%;"></div>
                    </div>
                    <span class="fw-medium small">${branch.attendance_rate}%</span>
                </div>
            </td>
            <td>${branch.online_devices} / ${branch.total_devices}</td>
        </tr>
    `).join("");
}

function renderAlerts(alerts) {
    const list = document.getElementById("alertsList");
    if (!alerts || alerts.length === 0) {
        list.innerHTML = `
            <div class="list-group-item text-center py-3">
                <div class="text-muted">لا توجد تنبيهات</div>
            </div>
        `;
        return;
    }
    
    list.innerHTML = alerts.map(alert => {
        const alertClass = alert.type === "device_offline" ? "list-group-item-warning" : "list-group-item-danger";
        const icon = alert.type === "device_offline" ? "bi-wifi-off" : "bi-exclamation-circle";
        return `
            <div class="list-group-item ${alertClass} border-0 d-flex gap-2 align-items-center">
                <i class="bi ${icon} fs-5"></i>
                <div class="flex-grow-1">
                    <div class="fw-medium">${alert.title}</div>
                    <div class="small">${alert.message}</div>
                </div>
            </div>
        `;
    }).join("");
}

function renderRecentLogs(logs) {
    const tbody = document.getElementById("recentLogsTableBody");
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${new Date(log.check_time).toLocaleString("ar-EG")}</td>
            <td>${log.employee_name || "-"}</td>
            <td>${log.branch_name || "-"}</td>
            <td><span class="badge ${attendanceTypeBadgeMap[log.attendance_type] || "bg-secondary"}">${attendanceTypeMap[log.attendance_type] || log.attendance_type}</span></td>
        </tr>
    `).join("");
}
