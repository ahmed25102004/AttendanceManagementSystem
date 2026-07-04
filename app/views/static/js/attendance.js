async function loadAttendanceEmployees() {
    const employees = await fetchJSON("/api/employees");
    const checkInSelect = document.getElementById("attendance_employee_id");
    const checkOutSelect = document.getElementById("checkout_employee_id");
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
    const query = dateValue ? `?attendance_date=${dateValue}` : "";
    const records = await fetchJSON(`/api/attendance${query}`);
    const tbody = document.getElementById("attendanceTableBody");
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

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    await hydrateUser();

    try {
        await loadAttendanceEmployees();
        await loadAttendanceRecords();
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
