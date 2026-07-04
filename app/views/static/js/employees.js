
const employeeCache = new Map();
const departmentCache = new Map();
let selectedEmployeeId = null;

function showAlert(alertId, message, type = "danger") {
  const el = document.getElementById(alertId);
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
  const selectEl = document.getElementById("department_id");
  selectEl.innerHTML = '<option value="">-- اختر القسم --</option>';
  departmentCache.clear();

  departments.forEach((dept) => {
    departmentCache.set(dept.id, dept);
    const option = document.createElement("option");
    option.value = dept.id;
    option.textContent = dept.name;
    selectEl.appendChild(option);
  });
}

async function loadEmployees() {
    const employees = await fetchJSON("/api/employees");
    const tbody = document.getElementById("employeeTableBody");
    tbody.innerHTML = "";
    employeeCache.clear();
    
    const employmentTypeLabels = {
        "full_time": "دوام كامل",
        "part_time": "دوام جزئي",
        "contract": "عقد عمل",
        "internship": "تدريب"
    };

    employees.forEach((employee) => {
        employeeCache.set(employee.id, employee);
        const dept = employee.department_id ? departmentCache.get(employee.department_id) : null;
        tbody.innerHTML += `
            <tr>
                <td>${employee.full_name}</td>
                <td>${dept ? dept.name : "-"}</td>
                <td>${employee.phone || "-"}</td>
                <td>${employee.hire_date}</td>
                <td>${employee.job_title}</td>
                <td>${employmentTypeLabels[employee.employment_type] || employee.employment_type}</td>
                <td>${employee.role === 'admin' ? 'مدير' : 'موظف'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="editEmployee(${employee.id})">تعديل</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteEmployee(${employee.id})">حذف</button>
                </td>
            </tr>
        `;
    });
}

function resetEmployeeForm() {
  document.getElementById("employeeForm").reset();
  document.getElementById("employeeId").value = "";
  document.getElementById("department_id").value = "";
}

function editEmployee(employeeId) {
    const employee = employeeCache.get(employeeId);
    if (!employee) {
        showAlert("employeeAlert", "تعذر تحميل بيانات الموظف.");
        return;
    }

    document.getElementById("employeeId").value = employee.id;
    document.getElementById("full_name").value = employee.full_name;
    document.getElementById("phone").value = employee.phone || "";
    document.getElementById("address").value = employee.address || "";
    document.getElementById("job_title").value = employee.job_title;
    document.getElementById("hire_date").value = employee.hire_date;
    document.getElementById("user_role").value = employee.role || "employee";
    document.getElementById("department_id").value = employee.department_id || "";
    document.getElementById("employment_type").value = employee.employment_type || "full_time";
}

async function deleteEmployee(employeeId) {
  if (!confirm("هل تريد حذف هذا الموظف؟")) {
    return;
  }

  try {
    await fetchJSON(`/api/employees/${employeeId}`, { method: "DELETE" });
    await loadEmployees();
    showAlert("employeeAlert", "تم حذف الموظف بنجاح.", "success");
  } catch (error) {
    showAlert("employeeAlert", error.message);
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
        await loadEmployees();
    } catch (error) {
        showAlert("employeeAlert", error.message);
    }

    document.getElementById("employeeForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const employeeId = document.getElementById("employeeId").value;

        const payload = {
                full_name: document.getElementById("full_name").value.trim(),
                role: document.getElementById("user_role").value || "employee",
                phone: document.getElementById("phone").value.trim() || null,
                address: document.getElementById("address").value.trim() || null,
                job_title: document.getElementById("job_title").value.trim(),
                hire_date: document.getElementById("hire_date").value,
                department_id: document.getElementById("department_id").value ? parseInt(document.getElementById("department_id").value, 10) : null,
                employment_type: document.getElementById("employment_type").value || "full_time",
            };

        const method = employeeId ? "PUT" : "POST";
        const url = employeeId ? `/api/employees/${employeeId}` : "/api/employees";

        try {
            await fetchJSON(url, {
                method: method,
                body: JSON.stringify(payload),
            });
            resetEmployeeForm();
            await loadEmployees();
            showAlert("employeeAlert", employeeId ? "تم تحديث بيانات الموظف بنجاح." : "تم إضافة الموظف بنجاح.", "success");
        } catch (error) {
            showAlert("employeeAlert", error.message);
        }
    });
    
    document.getElementById("uploadDocumentForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        
        if (!selectedEmployeeId) return;
        
        const formData = new FormData();
        formData.append("employee_id", selectedEmployeeId);
        formData.append("name", document.getElementById("docName").value);
        formData.append("notes", document.getElementById("docNotes").value);
        formData.append("file", document.getElementById("docFile").files[0]);
        
        try {
            const token = getToken();
            await fetch(`/api/employee-documents/`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });
            
            document.getElementById("uploadDocumentForm").reset();
            await loadEmployeeDocuments(selectedEmployeeId);
            showAlert("employeeAlert", "تم رفع المستند بنجاح", "success");
        } catch (error) {
            showAlert("employeeAlert", "حدث خطأ أثناء رفع المستند");
        }
    });
});

