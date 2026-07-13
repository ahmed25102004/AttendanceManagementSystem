async function renderReport(url) {
    const rows = await fetchJSON(url);
    const tbody = document.getElementById("reportTableBody");
    tbody.innerHTML = "";

    rows.forEach((row) => {
        const statusLabel = row.status === "present" ? "حاضر" : row.status === "absent" ? "غائب" : row.status;
        tbody.innerHTML += `
            <tr>
                <td>${row.employee_code}</td>
                <td>${row.employee_name}</td>
                <td>${row.department || "-"}</td>
                <td>${row.job_title}</td>
                <td>${row.attendance_date}</td>
                <td>${row.check_in_time ? new Date(row.check_in_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${row.check_out_time ? new Date(row.check_out_time).toLocaleString("ar-EG") : "-"}</td>
                <td>${row.working_hours}</td>
                <td>${statusLabel}</td>
                <td>${row.is_late ? "نعم" : "لا"}</td>
            </tr>
        `;
    });
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
            link.download = fileNameMatch ? fileNameMatch[1] : "report";
            link.click();
            window.URL.revokeObjectURL(url);
        })
        .catch((error) => showAlert("reportAlert", error.message));
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();

    document.getElementById("dailyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("daily_report_date").value;
        try {
            await renderReport(`/api/reports/daily?report_date=${reportDate}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("weeklyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const reportDate = document.getElementById("weekly_report_date").value;
        try {
            await renderReport(`/api/reports/weekly?report_date=${reportDate}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("monthlyReportForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const month = document.getElementById("monthly_report_month").value;
        try {
            await renderReport(`/api/reports/monthly?month=${month}`);
        } catch (error) {
            showAlert("reportAlert", error.message);
        }
    });

    document.getElementById("exportDailyExcel").addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/excel?report_date=${reportDate}`);
    });

    document.getElementById("exportDailyPdf").addEventListener("click", () => {
        const reportDate = document.getElementById("daily_report_date").value;
        securedDownload(`/api/reports/daily/export/pdf?report_date=${reportDate}`);
    });

    document.getElementById("exportWeeklyExcel").addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/excel?report_date=${reportDate}`);
    });

    document.getElementById("exportWeeklyPdf").addEventListener("click", () => {
        const reportDate = document.getElementById("weekly_report_date").value;
        securedDownload(`/api/reports/weekly/export/pdf?report_date=${reportDate}`);
    });

    document.getElementById("exportMonthlyExcel").addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        securedDownload(`/api/reports/monthly/export/excel?month=${month}`);
    });

    document.getElementById("exportMonthlyPdf").addEventListener("click", () => {
        const month = document.getElementById("monthly_report_month").value;
        securedDownload(`/api/reports/monthly/export/pdf?month=${month}`);
    });
});
