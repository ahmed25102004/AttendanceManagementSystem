
const employeeCache = new Map();
const departmentCache = new Map();
const branchCache = new Map();
const shiftCache = new Map();
let selectedEmployeeId = null;
let allEmployees = [];
let currentView = "table"; // "table" or "card"

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
  branchCache.clear();

  branches.forEach((branch) => {
    branchCache.set(branch.id, branch);
  });
}

async function loadDepartments() {
  const departments = await fetchJSON("/api/departments");
  const selectEl = document.getElementById("department_id");
  const filterSelectEl = document.getElementById("filterDepartment");
  if (selectEl) {
    selectEl.innerHTML = '<option value="">-- اختر القسم --</option>';
  }
  if (filterSelectEl) {
    filterSelectEl.innerHTML = '<option value="">كل الأقسام</option>';
  }
  departmentCache.clear();

  departments.forEach((dept) => {
    departmentCache.set(dept.id, dept);
    if (selectEl) {
      const option = document.createElement("option");
      option.value = dept.id;
      option.textContent = dept.name;
      selectEl.appendChild(option);
    }
    if (filterSelectEl) {
      const option = document.createElement("option");
      option.value = dept.id;
      option.textContent = dept.name;
      filterSelectEl.appendChild(option);
    }
  });
}

async function loadShifts() {
  const shifts = await fetchJSON("/api/shifts");
  const selectEl = document.getElementById("shift_id");
  if (!selectEl) return;
  selectEl.innerHTML = '<option value="">-- بدون وردية افتراضية --</option>';
  shiftCache.clear();

  shifts.forEach((shift) => {
    shiftCache.set(shift.id, shift);
    const option = document.createElement("option");
    option.value = shift.id;
    option.textContent = `${shift.name} (${shift.start_time} - ${shift.end_time})`;
    selectEl.appendChild(option);
  });
}

async function loadEmployees() {
        allEmployees = await fetchJSON("/api/employees?all=true");
        employeeCache.clear();
        allEmployees.forEach(emp => employeeCache.set(emp.id, emp));
        renderEmployees();
}

function renderEmployees() {
  const currentBranchId = getCurrentBranchId(); // Auto filter by current branch
  const searchTerm = (document.getElementById("employeeSearch").value || "").toLowerCase();
  const filterDepartment = document.getElementById("filterDepartment").value;
  const filterEmploymentType = document.getElementById("filterEmploymentType").value;
  const filterActiveStatus = document.getElementById("filterActiveStatus").value;
  
  let filteredEmployees = allEmployees.filter(emp => 
    (emp.full_name && emp.full_name.toLowerCase().includes(searchTerm)) || 
    (emp.employee_code && emp.employee_code.toLowerCase().includes(searchTerm))
  );
  
  // Auto-filter by current branch
  if (currentBranchId) {
    filteredEmployees = filteredEmployees.filter(emp => emp.branch_id === Number(currentBranchId));
  }
  
  if (filterDepartment) {
    filteredEmployees = filteredEmployees.filter(emp => emp.department_id === Number(filterDepartment));
  }
  if (filterEmploymentType) {
    filteredEmployees = filteredEmployees.filter(emp => emp.employment_type === filterEmploymentType);
  }
  if (filterActiveStatus) {
    const isActive = filterActiveStatus === "true";
    filteredEmployees = filteredEmployees.filter(emp => emp.is_active === isActive);
  }
  
  // Update table columns based on filtered department policy
  const dept = filterDepartment ? departmentCache.get(parseInt(filterDepartment)) : null;
  const requirements = dept ? getPolicyRequirements(dept.attendance_policy) : getPolicyRequirements("default");
  
  const shiftColumn = document.getElementById("shiftColumn");
  const restDayColumn = document.getElementById("restDayColumn");
  
  if (shiftColumn) {
    shiftColumn.style.display = requirements.showShiftField ? "" : "none";
  }
  if (restDayColumn) {
    restDayColumn.style.display = requirements.showWeeklyRestDayField ? "" : "none";
  }
  
  renderTableView(filteredEmployees, requirements);
  renderCardView(filteredEmployees, requirements);
}

function renderTableView(employees, requirements) {
  const tbody = document.getElementById("employeeTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  const employmentTypeLabels = {
    "full_time": "دوام كامل",
    "part_time": "دوام جزئي",
    "contract": "عقد عمل",
    "internship": "تدريب"
  };

  employees.forEach((employee) => {
    const dept = employee.department_id ? departmentCache.get(employee.department_id) : null;
    const shift = employee.shift_id ? shiftCache.get(employee.shift_id) : null;
    const statusBadge = employee.is_active 
      ? '<span class="badge bg-success">نشط</span>' 
      : '<span class="badge bg-secondary">غير نشط</span>';
    tbody.innerHTML += `
      <tr>
        <td><span class="fw-medium">${employee.employee_code}</span></td>
        <td><span class="fw-medium">${employee.full_name}</span></td>
        <td>${dept ? dept.name : "-"}</td>
        <td>${employee.phone || "-"}</td>
        <td>${employee.hire_date}</td>
        <td>${employee.job_title}</td>
        <td>${employmentTypeLabels[employee.employment_type] || employee.employment_type}</td>
        <td style="display: ${requirements.showShiftField ? '' : 'none'}">${shift ? shift.name : "-"}</td>
        <td style="display: ${requirements.showWeeklyRestDayField ? '' : 'none'}">${employee.weekly_rest_day || "-"}</td>
        <td>${statusBadge}</td>
        <td>
          <div class="d-flex gap-1 flex-nowrap">
            <button class="btn btn-sm btn-outline-success" onclick="window.location.href='/employees/${employee.id}'"><i class="bi bi-person"></i></button>
            <button class="btn btn-sm btn-outline-info" onclick="viewDocuments(${employee.id}, '${employee.full_name}')"><i class="bi bi-file-earmark-text"></i></button>
            <button class="btn btn-sm btn-outline-primary" onclick="editEmployee(${employee.id})"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteEmployee(${employee.id})"><i class="bi bi-trash"></i></button>
          </div>
        </td>
      </tr>
    `;
  });
}

function renderCardView(employees, requirements) {
  const cardContainer = document.getElementById("cardView");
  if (!cardContainer) return;
  cardContainer.innerHTML = "";
  
  const employmentTypeLabels = {
    "full_time": "دوام كامل",
    "part_time": "دوام جزئي",
    "contract": "عقد عمل",
    "internship": "تدريب"
  };

  employees.forEach((employee) => {
    const dept = employee.department_id ? departmentCache.get(employee.department_id) : null;
    const shift = employee.shift_id ? shiftCache.get(employee.shift_id) : null;
    const statusBadge = employee.is_active 
      ? '<span class="badge bg-success">نشط</span>' 
      : '<span class="badge bg-secondary">غير نشط</span>';
    cardContainer.innerHTML += `
      <div class="col-lg-4 col-md-6">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <h5 class="card-title fw-bold mb-0 text-truncate">${employee.full_name}</h5>
              ${statusBadge}
            </div>
            <h6 class="card-subtitle text-muted mb-3"><i class="bi bi-person-badge me-1"></i>${employee.employee_code}</h6>
            <div class="mb-2">
              <i class="bi bi-door-open me-2"></i> <span class="text-muted">القسم:</span> ${dept ? dept.name : "-"}
            </div>
            <div class="mb-2">
              <i class="bi bi-briefcase me-2"></i> <span class="text-muted">الوظيفة:</span> ${employee.job_title}
            </div>
            <div class="mb-2">
              <i class="bi bi-clock me-2"></i> <span class="text-muted">التوظيف:</span> ${employmentTypeLabels[employee.employment_type] || employee.employment_type}
            </div>
            <div class="mb-2" style="display: ${requirements.showShiftField ? '' : 'none'}">
              <i class="bi bi-calendar2-week me-2"></i> <span class="text-muted">الوردية:</span> ${shift ? shift.name : "-"}
            </div>
            <div class="mb-3" style="display: ${requirements.showWeeklyRestDayField ? '' : 'none'}">
              <i class="bi bi-calendar-day me-2"></i> <span class="text-muted">الإجازة الأسبوعية:</span> ${employee.weekly_rest_day || "-"}
            </div>
            <div class="d-flex gap-2 pt-2 border-top border-light">
              <button class="btn btn-sm btn-outline-success flex-grow-1" onclick="window.location.href='/employees/${employee.id}'">
                <i class="bi bi-person"></i> ملف الموظف
              </button>
              <button class="btn btn-sm btn-outline-info" onclick="viewDocuments(${employee.id}, '${employee.full_name}')">
                <i class="bi bi-file-earmark-text"></i>
              </button>
              <button class="btn btn-sm btn-outline-primary" onclick="editEmployee(${employee.id})">
                <i class="bi bi-pencil"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" onclick="deleteEmployee(${employee.id})">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
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

function getPolicyRequirements(attendancePolicy) {
  // Define which fields are required for each policy
  const requirements = {
    // Default policy: show all fields
    "default": {
      showShiftField: true,
      showWeeklyRestDayField: false
    },
    // Leather policy: show minimal fields
    "leather_department": {
      showShiftField: false,
      showWeeklyRestDayField: false
    },
    // Reception policy: show both shift and weekly rest day
    "reception_department": {
      showShiftField: true,
      showWeeklyRestDayField: true
    },
    // Workers policy: same as reception
    "workers_department": {
      showShiftField: true,
      showWeeklyRestDayField: true
    },
    // Doctors policy: show shift field
    "doctors_department": {
      showShiftField: true,
      showWeeklyRestDayField: false
    }
  };
  
  return requirements[attendancePolicy] || requirements["default"];
}

function updateDepartmentSpecificFields() {
  const departmentId = el("department_id").value;
  const dept = departmentId ? departmentCache.get(parseInt(departmentId)) : null;
  
  const requirements = dept ? getPolicyRequirements(dept.attendance_policy) : getPolicyRequirements("default");
  
  // Update visibility and clear value of shift field
  const shiftField = document.getElementById("shiftField");
  if (shiftField) {
    shiftField.style.display = requirements.showShiftField ? "block" : "none";
    if (!requirements.showShiftField) {
      el("shift_id").value = "";
    }
  }
  
  // Update visibility and clear value of weekly rest day field
  const weeklyRestDayField = document.getElementById("weeklyRestDayField");
  if (weeklyRestDayField) {
    weeklyRestDayField.style.display = requirements.showWeeklyRestDayField ? "block" : "none";
    if (!requirements.showWeeklyRestDayField) {
      el("weekly_rest_day").value = "";
    }
  }
}

function resetEmployeeForm() {
  const form = document.getElementById("employeeForm");
  if (form) form.reset();
  el("employeeId").value = "";
  el("department_id").value = "";
  el("shift_id").value = "";
  el("weekly_rest_day").value = "";
  updateDepartmentSpecificFields();
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
  el("employment_type").value = employee.employment_type || "full_time";
  el("shift_id").value = employee.shift_id || "";
  el("weekly_rest_day").value = employee.weekly_rest_day || "";
  updateDepartmentSpecificFields();
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
        await loadShifts();
        await loadEmployees();
        // Initialize fields visibility
        updateDepartmentSpecificFields();
    } catch (error) {
        showAlert("employeeAlert", error.message);
    }

    // Search and filters handling
    document.getElementById("employeeSearch").addEventListener("input", () => {
      renderEmployees();
    });
    document.getElementById("filterDepartment").addEventListener("change", () => {
      renderEmployees();
    });
    document.getElementById("filterEmploymentType").addEventListener("change", () => {
      renderEmployees();
    });
    document.getElementById("filterActiveStatus").addEventListener("change", () => {
      renderEmployees();
    });
    
    // View toggle
    document.getElementById("tableViewBtn").addEventListener("click", () => {
      currentView = "table";
      document.getElementById("tableView").style.display = "block";
      document.getElementById("cardView").style.display = "none";
      document.getElementById("tableViewBtn").classList.add("active");
      document.getElementById("cardViewBtn").classList.remove("active");
    });
    document.getElementById("cardViewBtn").addEventListener("click", () => {
      currentView = "card";
      document.getElementById("tableView").style.display = "none";
      document.getElementById("cardView").style.display = "flex";
      document.getElementById("tableViewBtn").classList.remove("active");
      document.getElementById("cardViewBtn").classList.add("active");
    });

    // Update fields when department is selected
    const departmentSelect = document.getElementById("department_id");
    if (departmentSelect) {
      departmentSelect.addEventListener("change", () => {
        updateDepartmentSpecificFields();
      });
    }

    const form = document.getElementById("employeeForm");
    if (form) {
      form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const employeeId = el("employeeId").value;

          const currentBranchId = getCurrentBranchId();
          const departmentId = el("department_id").value ? parseInt(el("department_id").value, 10) : null;
          const dept = departmentId ? departmentCache.get(departmentId) : null;
          const requirements = dept ? getPolicyRequirements(dept.attendance_policy) : getPolicyRequirements("default");
          
          const payload = {
                  employee_code: el("employee_code").value.trim(),
                  full_name: el("full_name").value.trim(),
                  role: "employee",
                  phone: el("phone").value.trim() || null,
                  address: el("address").value.trim() || null,
                  job_title: el("job_title").value.trim(),
                  hire_date: el("hire_date").value,
                  department_id: departmentId,
                  branch_id: currentBranchId ? parseInt(currentBranchId, 10) : null, // Auto-set to current branch
                  employment_type: el("employment_type").value || "full_time",
              };
          
          // Add shift field only if it's required by the policy
          if (requirements.showShiftField) {
            payload.shift_id = el("shift_id").value ? parseInt(el("shift_id").value, 10) : null;
          }
          
          // Add weekly rest day field only if it's required by the policy
          if (requirements.showWeeklyRestDayField) {
            payload.weekly_rest_day = el("weekly_rest_day").value || null;
          }

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
