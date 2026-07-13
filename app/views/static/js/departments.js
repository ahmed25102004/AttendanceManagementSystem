
const departmentCache = new Map();

function showDepartmentAlert(message, type = "danger") {
    const element = document.getElementById("departmentAlert");
    if (!element) return;
    element.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    setTimeout(() => {
        element.innerHTML = "";
    }, 3000);
}

async function loadDepartments() {
    const departments = await fetchJSON("/api/departments");
    const tbody = document.getElementById("departmentTableBody");
    if (!tbody) return;
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
    const form = document.getElementById("departmentForm");
    if (form) form.reset();
    el("departmentId").value = "";
}

function editDepartment(departmentId) {
    const department = departmentCache.get(departmentId);
    if (!department) {
        showDepartmentAlert("تعذر تحميل بيانات القسم.");
        return;
    }

    el("departmentId").value = department.id;
    el("departmentName").value = department.name;
    el("departmentDescription").value = department.description || "";
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
    const user = await hydrateUser();

    try {
        await loadDepartments();
    } catch (error) {
        showDepartmentAlert(error.message);
    }

    const form = document.getElementById("departmentForm");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const departmentId = el("departmentId").value;

            const payload = {
                name: el("departmentName").value.trim(),
                description: el("departmentDescription").value.trim() || null,
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
    }
});

