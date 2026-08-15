document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadBranchSelector();

    let currentSettings = null;

    async function loadSettings() {
        try {
            currentSettings = await fetchJSON("/api/settings");
            if (!currentSettings) return;

            if (el("company_name")) el("company_name").value = currentSettings.company_name || "";
            if (el("auto_backup_enabled")) el("auto_backup_enabled").checked = Boolean(currentSettings.auto_backup_enabled);
            if (el("auto_backup_time")) el("auto_backup_time").value = currentSettings.auto_backup_time ? currentSettings.auto_backup_time.substring(0, 5) : "02:00";
            if (el("auto_backup_retention_days")) el("auto_backup_retention_days").value = currentSettings.auto_backup_retention_days || 30;
        } catch (error) {
            console.error("Error loading system settings:", error);
            showAlert("settingsAlert", error.message);
        }
    }

    try {
        await loadSettings();
    } catch (error) {
        showAlert("settingsAlert", error.message);
    }

    const settingsForm = document.getElementById("settingsForm");
    if (settingsForm) {
        settingsForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!currentSettings) currentSettings = {};

            const payload = {
                company_name: el("company_name").value.trim(),
                workplace_latitude: currentSettings.workplace_latitude ?? null,
                workplace_longitude: currentSettings.workplace_longitude ?? null,
                workplace_radius_meters: currentSettings.workplace_radius_meters ?? 150,
                allowed_ip_ranges: currentSettings.allowed_ip_ranges ?? [],
                enforce_geofence: currentSettings.enforce_geofence ?? false,
                enforce_ip_check: currentSettings.enforce_ip_check ?? false,
                face_match_threshold: currentSettings.face_match_threshold ?? 0.45,
                check_in_open_time: currentSettings.check_in_open_time ?? "07:30:00",
                check_in_close_time: currentSettings.check_in_close_time ?? "10:00:00",
                check_out_open_time: currentSettings.check_out_open_time ?? "16:00:00",
                check_out_close_time: currentSettings.check_out_close_time ?? "19:00:00",
                auto_backup_enabled: Boolean(el("auto_backup_enabled").checked),
                auto_backup_time: el("auto_backup_time").value ? (el("auto_backup_time").value.length === 5 ? el("auto_backup_time").value + ":00" : el("auto_backup_time").value) : "02:00:00",
                auto_backup_retention_days: Number(el("auto_backup_retention_days").value) || 30,
                zkteco_enabled: currentSettings.zkteco_enabled ?? false,
                zkteco_ip: currentSettings.zkteco_ip ?? "192.168.1.201",
                zkteco_port: currentSettings.zkteco_port ?? 4370,
                zkteco_password: currentSettings.zkteco_password ?? "",
                zkteco_auto_sync_enabled: currentSettings.zkteco_auto_sync_enabled ?? false,
                zkteco_auto_sync_interval_minutes: currentSettings.zkteco_auto_sync_interval_minutes ?? 30,
            };

            try {
                await fetchJSON("/api/settings", {
                    method: "PUT",
                    body: JSON.stringify(payload),
                });
                await loadSettings();
                showAlert("settingsAlert", "تم حفظ إعدادات النظام والنسخ الاحتياطي بنجاح.", "success");
            } catch (error) {
                console.error("Error updating settings:", error);
                showAlert("settingsAlert", error.message);
            }
        });
    }
});
