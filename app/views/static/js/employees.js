
const employeeCache = new Map();
const departmentCache = new Map();
const branchCache = new Map();
let selectedEmployeeId = null;

function showAlert(alertId, message, type = "danger") {
  const element = document.getElementById(alertId);
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

async function loadBranches() {
  const branches = await fetchJSON("/api/branches?all=true");
  const selectEl = document.getElementById("employee_branch_id");
  if (!selectEl) return;
  selectEl.innerHTML = '<option value="">-- اختر الفرع --</option>';
  branchCache.clear();

  branches.forEach((branch) => {
    branchCache.set(branch.id, branch);
    const option = document.createElement("option");
    option.value = branch.id;
    option.textContent = branch.name;
    selectEl.appendChild(option);
  });
  
  // Auto-select current branch
  const currentBranchId = getCurrentBranchId();
  if (currentBranchId && branchCache.has(parseInt(currentBranchId))) {
    selectEl.value = currentBranchId;
  }
}

async function loadDepartments() {
  const departments = await fetchJSON("/api/departments");
  const selectEl = document.getElementById("department_id");
  if (!selectEl) return;
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
        const employees = await fetchJSON("/api/employees?all=true");
        const tbody = document.getElementById("employeeTableBody");
        if (!tbody) return;
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
            const branch = employee.branch_id ? branchCache.get(employee.branch_id) : null;
            tbody.innerHTML += `
                <tr>
                    <td>${employee.employee_code}</td>
                    <td>${employee.full_name}</td>
                    <td>${branch ? branch.name : "-"}</td>
                    <td>${dept ? dept.name : "-"}</td>
                    <td>${employee.phone || "-"}</td>
                    <td>${employee.hire_date}</td>
                    <td>${employee.job_title}</td>
                    <td>${employmentTypeLabels[employee.employment_type] || employee.employment_type}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-info ms-2" onclick="viewDocuments(${employee.id}, '${employee.full_name}')">مستندات</button>
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="editEmployee(${employee.id})">تعديل</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteEmployee(${employee.id})">حذف</button>
                    </td>
                </tr>
            `;
        });
    }

async function loadEmployeeDocuments(employeeId) {
  const documents = await fetchJSON(`/api/employee-documents/${employeeId}`);
  const tbody = document.getElementById("documentsTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  documents.forEach((doc) => {
    tbody.innerHTML += `
            <tr>
                <td>${doc.name}</td>
                <td>${doc.notes || "-"}</td>
                <td>${doc.upload_date}</td>
                <td>
                    <a href="/api/employee-documents/download/${doc.id}" class="btn btn-sm btn-outline-primary" target="_blank">تحميل</a>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDocument(${doc.id})">حذف</button>
                </td>
            </tr>
        `;
  });
}

function viewDocuments(employeeId, employeeName) {
  selectedEmployeeId = employeeId;
  const docNameEl = document.getElementById("documentEmployeeName");
  const docsSectionEl = document.getElementById("documentsSection");
  if (docNameEl) docNameEl.textContent = employeeName;
  if (docsSectionEl) docsSectionEl.style.display = "block";
  loadEmployeeDocuments(employeeId);
}

async function deleteDocument(docId) {
  if (!confirm("هل تريد حذف هذا المستند؟")) return;
  try {
    await fetchJSON(`/api/employee-documents/${docId}`, { method: "DELETE" });
    await loadEmployeeDocuments(selectedEmployeeId);
    showAlert("employeeAlert", "تم حذف المستند بنجاح.", "success");
  } catch (error) {
    showAlert("employeeAlert", error.message);
  }
}

function resetEmployeeForm() {
  const form = document.getElementById("employeeForm");
  if (form) form.reset();
  el("employeeId").value = "";
  el("department_id").value = "";
  el("employee_branch_id").value = "";
}

function editEmployee(employeeId) {
  const employee = employeeCache.get(employeeId);
  if (!employee) {
    showAlert("employeeAlert", "تعذر تحميل بيانات الموظف.");
    return;
  }

  el("employeeId").value = employee.id;
  el("employee_code").value = employee.employee_code;
  el("full_name").value = employee.full_name;
  el("phone").value = employee.phone || "";
  el("address").value = employee.address || "";
  el("job_title").value = employee.job_title;
  el("hire_date").value = employee.hire_date;
  el("department_id").value = employee.department_id || "";
  el("employee_branch_id").value = employee.branch_id || "";
  el("employment_type").value = employee.employment_type || "full_time";
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
    // requireAuth();
    const user = await hydrateUser();
    // if (!user) return;
    // if (user.role !== "admin") {
    //     window.location.href = "/my-attendance";
    //     return;
    // }

    try {
        await loadBranches();
        await loadDepartments();
        await loadEmployees();
    } catch (error) {
        showAlert("employeeAlert", error.message);
    }

    const form = document.getElementById("employeeForm");
    if (form) {
      form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const employeeId = el("employeeId").value;

          const payload = {
                  employee_code: el("employee_code").value.trim(),
                  full_name: el("full_name").value.trim(),
                  role: "employee",
                  phone: el("phone").value.trim() || null,
                  address: el("address").value.trim() || null,
                  job_title: el("job_title").value.trim(),
                  hire_date: el("hire_date").value,
                  department_id: el("department_id").value ? parseInt(el("department_id").value, 10) : null,
                  branch_id: el("employee_branch_id").value ? parseInt(el("employee_branch_id").value, 10) : null,
                  employment_type: el("employment_type").value || "full_time",
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
    }
    
    const uploadForm = document.getElementById("uploadDocumentForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", async (event) => {
          event.preventDefault();
          
          if (!selectedEmployeeId) return;
          
          const formData = new FormData();
          formData.append("employee_id", selectedEmployeeId);
          formData.append("name", el("docName").value);
          formData.append("notes", el("docNotes").value);
          formData.append("file", el("docFile").files[0]);
          
          try {
              const token = getToken();
              await fetch(`/api/employee-documents/`, {
                  method: "POST",
                  headers: {
                      "Authorization": `Bearer ${token}`
                  },
                  body: formData
              });
              
              uploadForm.reset();
              await loadEmployeeDocuments(selectedEmployeeId);
              showAlert("employeeAlert", "تم رفع المستند بنجاح", "success");
          } catch (error) {
              showAlert("employeeAlert", "حدث خطأ أثناء رفع المستند");
          }
      });
    }
});

