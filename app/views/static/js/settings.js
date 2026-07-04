document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    await hydrateUser();

    async function loadSettings() {
        const settings = await fetchJSON("/api/settings");
        document.getElementById("company_name").value = settings.company_name;
        document.getElementById("work_start_time").value = settings.work_start_time;
        document.getElementById("work_end_time").value = settings.work_end_time;
        document.getElementById("late_grace_minutes").value = settings.late_grace_minutes;
        document.getElementById("workplace_latitude").value = settings.workplace_latitude ?? "";
        document.getElementById("workplace_longitude").value = settings.workplace_longitude ?? "";
        document.getElementById("workplace_radius_meters").value = settings.workplace_radius_meters;
        document.getElementById("allowed_ip_ranges").value = (settings.allowed_ip_ranges || []).join(", ");
        document.getElementById("enforce_geofence").checked = settings.enforce_geofence;
        document.getElementById("enforce_ip_check").checked = settings.enforce_ip_check;
        document.getElementById("face_match_threshold").value = settings.face_match_threshold;
        document.getElementById("check_in_open_time").value = settings.check_in_open_time;
        document.getElementById("check_in_close_time").value = settings.check_in_close_time;
        document.getElementById("check_out_open_time").value = settings.check_out_open_time;
        document.getElementById("check_out_close_time").value = settings.check_out_close_time;
        document.getElementById("auto_backup_enabled").checked = settings.auto_backup_enabled;
        document.getElementById("auto_backup_time").value = settings.auto_backup_time;
        document.getElementById("auto_backup_retention_days").value = settings.auto_backup_retention_days;

        const weekendInputs = document.querySelectorAll("input[name='weekend_days']");
        weekendInputs.forEach((input) => {
            input.checked = settings.weekend_days.includes(input.value);
        });
    }

    try {
        await loadSettings();
    } catch (error) {
        showAlert("settingsAlert", error.message);
    }

    document.getElementById("settingsForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const weekendDays = Array.from(document.querySelectorAll("input[name='weekend_days']:checked")).map(
            (item) => item.value
        );

        try {
            await fetchJSON("/api/settings", {
                method: "PUT",
                body: JSON.stringify({
                    company_name: document.getElementById("company_name").value.trim(),
                    work_start_time: document.getElementById("work_start_time").value,
                    work_end_time: document.getElementById("work_end_time").value,
                    late_grace_minutes: Number(document.getElementById("late_grace_minutes").value),
                    weekend_days: weekendDays,
                    workplace_latitude: document.getElementById("workplace_latitude").value
                        ? Number(document.getElementById("workplace_latitude").value)
                        : null,
                    workplace_longitude: document.getElementById("workplace_longitude").value
                        ? Number(document.getElementById("workplace_longitude").value)
                        : null,
                    workplace_radius_meters: Number(document.getElementById("workplace_radius_meters").value),
                    allowed_ip_ranges: document
                        .getElementById("allowed_ip_ranges")
                        .value.split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    enforce_geofence: document.getElementById("enforce_geofence").checked,
                    enforce_ip_check: document.getElementById("enforce_ip_check").checked,
                    face_match_threshold: Number(document.getElementById("face_match_threshold").value),
                    check_in_open_time: document.getElementById("check_in_open_time").value,
                    check_in_close_time: document.getElementById("check_in_close_time").value,
                    check_out_open_time: document.getElementById("check_out_open_time").value,
                    check_out_close_time: document.getElementById("check_out_close_time").value,
                    auto_backup_enabled: document.getElementById("auto_backup_enabled").checked,
                    auto_backup_time: document.getElementById("auto_backup_time").value,
                    auto_backup_retention_days: Number(document.getElementById("auto_backup_retention_days").value),
                }),
            });
            showAlert("settingsAlert", "تم تحديث إعدادات المركز بنجاح.", "success");
        } catch (error) {
            showAlert("settingsAlert", error.message);
        }
    });
});
