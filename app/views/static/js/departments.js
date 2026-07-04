
const departmentCache = new Map();

function showDepartmentAlert(message, type = "danger") {
    const el = document.getElementById("departmentAlert");
    if (!el) return;
    el.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    setTimeout(() => {
        el.innerHTML = "";
    }, 3000);
}

async function loadDepartments() {
    const departments = await fetchJSON("/api/departments");
    const tbody = document.getElementById("departmentTableBody");
    tbody.innerHTML = "";
    departmentCache.clear();

    departments.forEach((department) => {
        departmentCache.set(department.id, department);
        tbody.innerHTML += `
            <tr>
                <td>${department.name}</td>
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
    document.getElementById("departmentForm").reset();
    document.getElementById("departmentId").value = "";
}

function editDepartment(departmentId) {
    const department = departmentCache.get(departmentId);
    if (!department) {
        showDepartmentAlert("تعذر تحميل بيانات القسم.");
        return;
    }

    document.getElementById("departmentId").value = department.id;
    document.getElementById("departmentName").value = department.name;
    document.getElementById("departmentDescription").value = department.description || "";
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
    requireAuth();
    const user = await hydrateUser();
    if (!user) return;
    if (user.role !== "admin") {
        window.location.href = "/my-attendance";
        return;
    }

    try {
        await loadDepartments();
    } catch (error) {
        showDepartmentAlert(error.message);
    }

    document.getElementById("departmentForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const departmentId = document.getElementById("departmentId").value;

        const payload = {
            name: document.getElementById("departmentName").value.trim(),
            description: document.getElementById("departmentDescription").value.trim() || null,
        };

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
});

