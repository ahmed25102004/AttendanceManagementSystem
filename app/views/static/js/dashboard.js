let attendanceLineChart = null;
let attendancePieChart = null;

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    await hydrateUser();

    try {
        const summary = await fetchJSON("/api/dashboard/summary");
        document.getElementById("totalEmployees").textContent = summary.total_employees;
        document.getElementById("presentToday").textContent = summary.present_today;
        document.getElementById("absentToday").textContent = summary.absent_today;
        document.getElementById("lateEmployees").textContent = summary.late_employees;
        
        // Line chart
        const lineCtx = document.getElementById("attendanceChart").getContext("2d");
        const labels = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"];
        attendanceLineChart = new Chart(lineCtx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "الحاضرون",
                        data: [summary.total_employees * 0.9, summary.total_employees, summary.total_employees * 0.95, summary.total_employees * 0.98, summary.total_employees, summary.total_employees * 0.75, summary.total_employees * 0.5],
                        borderColor: "#0d6efd",
                        backgroundColor: "rgba(13, 110, 253, 0.1)",
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: "المتأخرون",
                        data: [2, 1, 3, 0, 1, 0, 0],
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
        
        // Pie chart
        const pieCtx = document.getElementById("attendancePieChart").getContext("2d");
        attendancePieChart = new Chart(pieCtx, {
            type: "pie",
            data: {
                labels: ["الحاضرون", "الغائبون", "المتأخرون"],
                datasets: [
                    {
                        label: "عدد الموظفين",
                        data: [summary.present_today, summary.absent_today, summary.late_employees],
                        backgroundColor: [
                            "#198754",
                            "#dc3545",
                            "#ffc107"
                        ],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "bottom"
                    }
                }
            }
        });
        
    } catch (error) {
        showAlert("dashboardAlert", error.message);
    }
});
