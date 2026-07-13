document.addEventListener("DOMContentLoaded", async () => {
    // requireAuth();
    await hydrateUser();

    let currentSettings = null;

    async function loadSettings() {
        currentSettings = await fetchJSON("/api/settings");
        // Only load elements that actually present on the page
        el("company_name").value = currentSettings.company_name;
        el("work_start_time").value = currentSettings.work_start_time;
        el("work_end_time").value = currentSettings.work_end_time;
        el("late_grace_minutes").value = currentSettings.late_grace_minutes;
        el("auto_backup_enabled").checked = currentSettings.auto_backup_enabled;
        el("auto_backup_time").value = currentSettings.auto_backup_time;
        el("auto_backup_retention_days").value = currentSettings.auto_backup_retention_days;

        const weekendInputs = document.querySelectorAll("input[name='weekend_days']");
        weekendInputs.forEach((input) => {
            input.checked = currentSettings.weekend_days.includes(input.value);
        });
    }

    try {
        await loadSettings();
    } catch (error) {
        showAlert("settingsAlert", error.message);
    }

    el("settingsForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const weekendDays = Array.from(document.querySelectorAll("input[name='weekend_days']:checked")).map(
            (item) => item.value
        );

        // Build complete payload with all fields the schema expects
        const payload = {
            company_name: el("company_name").value.trim(),
            work_start_time: el("work_start_time").value,
            work_end_time: el("work_end_time").value,
            weekend_days: weekendDays,
            late_grace_minutes: Number(el("late_grace_minutes").value),
            workplace_latitude: currentSettings.workplace_latitude ?? null,
            workplace_longitude: currentSettings.workplace_longitude ?? null,
            workplace_radius_meters: currentSettings.workplace_radius_meters ?? 150,
            allowed_ip_ranges: currentSettings.allowed_ip_ranges ?? [],
            enforce_geofence: currentSettings.enforce_geofence ?? false,
            enforce_ip_check: currentSettings.enforce_ip_check ?? false,
            face_match_threshold: currentSettings.face_match_threshold ?? 0.45,
            check_in_open_time: currentSettings.check_in_open_time ?? "07:30",
            check_in_close_time: currentSettings.check_in_close_time ?? "10:00",
            check_out_open_time: currentSettings.check_out_open_time ?? "16:00",
            check_out_close_time: currentSettings.check_out_close_time ?? "19:00",
            auto_backup_enabled: el("auto_backup_enabled").checked,
            auto_backup_time: el("auto_backup_time").value,
            auto_backup_retention_days: Number(el("auto_backup_retention_days").value),
            zkteco_enabled: currentSettings.zkteco_enabled ?? false,
            zkteco_ip: currentSettings.zkteco_ip ?? "",
            zkteco_port: currentSettings.zkteco_port ?? 4370,
            zkteco_password: currentSettings.zkteco_password ?? "",
            zkteco_auto_sync_enabled: currentSettings.zkteco_auto_sync_enabled ?? false,
            zkteco_auto_sync_interval_minutes: currentSettings.zkteco_auto_sync_interval_minutes ?? 30,
        };

        console.log("Payload being sent:", payload);

        try {
            await fetchJSON("/api/settings", {
                method: "PUT",
                body: JSON.stringify(payload),
            });
            await loadSettings();
            showAlert("settingsAlert", "تم تحديث إعدادات المركز بنجاح.", "success");
        } catch (error) {
            console.error("Error updating settings:", error);
            showAlert("settingsAlert", error.message);
        }
    });
});
