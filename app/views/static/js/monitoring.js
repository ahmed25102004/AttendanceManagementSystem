async function loadMonitoringStats() {
    try {
        const stats = await fetchJSON("/api/monitoring/stats");
        
        document.getElementById("totalDevices").textContent = stats.total_devices;
        document.getElementById("onlineDevices").textContent = stats.online_devices;
        document.getElementById("offlineDevices").textContent = stats.offline_devices;
        document.getElementById("todayLogs").textContent = stats.logs_today;
        document.getElementById("lastDevice").textContent = stats.last_device_name || "لا يوجد";
        document.getElementById("lastLogTime").textContent = stats.last_log_time ? new Date(stats.last_log_time).toLocaleString('ar-EG') : "لا يوجد";
        
        const inactiveTbody = document.getElementById("inactiveDevices");
        inactiveTbody.innerHTML = "";
        stats.inactive_devices.forEach(d => {
            inactiveTbody.innerHTML += `
                <tr>
                    <td>${d.device_name}</td>
                    <td>${d.branch_name || "-"}</td>
                    <td>${d.last_seen ? new Date(d.last_seen).toLocaleString('ar-EG') : "لم يتصل قط"}</td>
                </tr>
            `;
        });
        
    } catch (error) {
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadMonitoringStats();
    
    // Refresh every 30 seconds!
    setInterval(loadMonitoringStats, 30000);
});
