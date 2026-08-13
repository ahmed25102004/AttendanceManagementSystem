
const employeeCache = new Map();
const departmentCache = new Map();
const branchCache = new Map();
let selectedEmployeeId = null;
let allEmployees = [];
let currentView = "table"; // "table" or "card"

const WEEKDAY_LABELS = {
  monday: "الاثنين",
  tuesday: "الثلاثاء",
  wednesday: "الأربعاء",
  thursday: "الخميس",
  friday: "الجمعة",
  saturday: "السبت",
  sunday: "الأحد"
};

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
  
  const requirements = getVisibleFieldRequirements(filteredEmployees, filterDepartment);
  
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

function getRestDayLabel(value) {
  return WEEKDAY_LABELS[value] || value || "-";
}

function getEmployeeRequirements(employee) {
  const dept = employee?.department_id ? departmentCache.get(employee.department_id) : null;
  return dept ? getPolicyRequirements(dept.attendance_policy) : getPolicyRequirements("default");
}

function getVisibleFieldRequirements(employees, filterDepartment) {
  const dept = filterDepartment ? departmentCache.get(parseInt(filterDepartment, 10)) : null;
  if (dept) {
    return getPolicyRequirements(dept.attendance_policy);
  }

  return employees.reduce((acc, employee) => {
    const requirements = getEmployeeRequirements(employee);
    return {
      showWeeklyRestDayField: acc.showWeeklyRestDayField || requirements.showWeeklyRestDayField
    };
  }, {
    showWeeklyRestDayField: false
  });
}

function renderTableView(employees, requirements) {
  const tbody = document.getElementById("employeeTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  if (employees.length === 0) {
      tbody.innerHTML = `
          <tr>
              <td colspan="9" class="text-center py-5">
                  <i class="bi bi-inboxes text-muted" style="font-size: 3rem;"></i>
                  <h5 class="mt-3 text-muted">لا يوجد موظفين</h5>
              </td>
          </tr>
      `;
      return;
  }

  const employmentTypeLabels = {
    "full_time": "دوام كامل",
    "part_time": "دوام جزئي",
    "contract": "عقد عمل",
    "internship": "تدريب"
  };

  employees.forEach((employee) => {
    const dept = employee.department_id ? departmentCache.get(employee.department_id) : null;
    const employeeRequirements = getEmployeeRequirements(employee);
    const statusBadge = employee.is_active 
      ? '<span class="badge bg-success bg-opacity-10 text-success rounded-pill px-3">نشط</span>' 
      : '<span class="badge bg-secondary bg-opacity-10 text-secondary rounded-pill px-3">غير نشط</span>';
      
    tbody.innerHTML += `
      <tr>
        <td class="px-4"><span class="badge bg-light text-dark border">${employee.employee_code}</span></td>
        <td>
            <div class="d-flex align-items-center">
                <div class="bg-primary bg-opacity-10 text-primary rounded-circle d-flex justify-content-center align-items-center me-3" style="width: 40px; height: 40px;">
                    <i class="bi bi-person-fill fs-5"></i>
                </div>
                <div>
                    <h6 class="mb-0 fw-bold">${employee.full_name}</h6>
                    <small class="text-muted">${employmentTypeLabels[employee.employment_type] || employee.employment_type}</small>
                </div>
            </div>
        </td>
        <td><span class="fw-medium">${dept ? dept.name : "-"}</span></td>
        <td><span class="text-muted small">${employee.job_title}</span></td>
        <td><span class="text-muted small"><i class="bi bi-calendar3 me-1"></i>${employee.hire_date}</span></td>
        <td dir="ltr" class="text-end text-muted small">${employee.phone || "-"}</td>
        <td style="display: ${requirements.showWeeklyRestDayField ? '' : 'none'}">${employeeRequirements.showWeeklyRestDayField ? getRestDayLabel(employee.weekly_rest_day) : "-"}</td>
        <td>${statusBadge}</td>
        <td class="px-4 text-end">
          <div class="btn-group shadow-sm rounded-3">
            <button class="btn btn-sm btn-light border" title="الملف الشخصي" onclick="window.location.href='/employees/${employee.id}'"><i class="bi bi-person text-success"></i></button>
            <button class="btn btn-sm btn-light border" title="المستندات" onclick="viewDocuments(${employee.id}, '${employee.full_name}')"><i class="bi bi-folder2-open text-info"></i></button>
            <button class="btn btn-sm btn-light border" title="تعديل" onclick="editEmployee(${employee.id})"><i class="bi bi-pencil text-primary"></i></button>
            <button class="btn btn-sm btn-light border" title="حذف" onclick="deleteEmployee(${employee.id})"><i class="bi bi-trash text-danger"></i></button>
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
  
  if (employees.length === 0) {
      cardContainer.innerHTML = `
          <div class="col-12 text-center py-5">
              <i class="bi bi-inboxes text-muted" style="font-size: 3rem;"></i>
              <h5 class="mt-3 text-muted">لا يوجد موظفين</h5>
          </div>
      `;
      return;
  }

  const employmentTypeLabels = {
    "full_time": "دوام كامل",
    "part_time": "دوام جزئي",
    "contract": "عقد عمل",
    "internship": "تدريب"
  };

  employees.forEach((employee) => {
    const dept = employee.department_id ? departmentCache.get(employee.department_id) : null;
    const employeeRequirements = getEmployeeRequirements(employee);
    const statusBadge = employee.is_active 
      ? '<span class="badge bg-success bg-opacity-10 text-success rounded-pill px-3">نشط</span>' 
      : '<span class="badge bg-secondary bg-opacity-10 text-secondary rounded-pill px-3">غير نشط</span>';
    cardContainer.innerHTML += `
      <div class="col-xl-3 col-lg-4 col-md-6">
        <div class="card h-100 shadow-sm border-0 rounded-4 overflow-hidden position-relative">
          <div class="bg-primary bg-opacity-10 p-3 pb-4 text-center">
              <div class="bg-white rounded-circle d-inline-flex justify-content-center align-items-center shadow-sm mb-2" style="width: 64px; height: 64px;">
                  <i class="bi bi-person-fill text-primary fs-2"></i>
              </div>
              <h5 class="fw-bold mb-1 text-truncate">${employee.full_name}</h5>
              <div class="small text-muted mb-2">${employee.job_title}</div>
              ${statusBadge}
          </div>
          <div class="card-body pt-3">
            <div class="d-flex justify-content-between mb-2 small">
                <span class="text-muted"><i class="bi bi-upc-scan me-1"></i>الكود</span>
                <span class="fw-bold text-dark">${employee.employee_code}</span>
            </div>
            <div class="d-flex justify-content-between mb-2 small">
                <span class="text-muted"><i class="bi bi-building me-1"></i>القسم</span>
                <span class="fw-medium">${dept ? dept.name : "-"}</span>
            </div>
            <div class="d-flex justify-content-between mb-2 small">
                <span class="text-muted"><i class="bi bi-telephone me-1"></i>الهاتف</span>
                <span class="fw-medium text-end" dir="ltr">${employee.phone || "-"}</span>
            </div>
            <div class="d-flex justify-content-between mb-3 small" style="display: ${requirements.showWeeklyRestDayField && employeeRequirements.showWeeklyRestDayField ? 'flex' : 'none'} !important">
                <span class="text-muted"><i class="bi bi-calendar-x me-1"></i>الإجازة</span>
                <span class="fw-medium">${getRestDayLabel(employee.weekly_rest_day)}</span>
            </div>
            
            <div class="d-flex gap-2 pt-3 border-top mt-auto">
              <button class="btn btn-sm btn-light flex-grow-1" onclick="window.location.href='/employees/${employee.id}'">
                <i class="bi bi-person text-success"></i>
              </button>
              <button class="btn btn-sm btn-light flex-grow-1" onclick="viewDocuments(${employee.id}, '${employee.full_name}')">
                <i class="bi bi-folder2-open text-info"></i>
              </button>
              <button class="btn btn-sm btn-light flex-grow-1" onclick="editEmployee(${employee.id})">
                <i class="bi bi-pencil text-primary"></i>
              </button>
              <button class="btn btn-sm btn-light flex-grow-1" onclick="deleteEmployee(${employee.id})">
                <i class="bi bi-trash text-danger"></i>
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
    // Workers policy: auto shift detection (NO manual shift selection), HAS weekly rest day
    "workers_department": {
      showShiftField: false,
      showWeeklyRestDayField: true
    },
    // Doctors policy: show shift field
    "doctors_department": {
      showShiftField: true,
      showWeeklyRestDayField: false
    },
    // Call Center policy: auto shift detection (NO manual shift selection), NO weekly rest day
    "call_center_department": {
      showShiftField: false,
      showWeeklyRestDayField: false
    }
  };
  
  return requirements[attendancePolicy] || requirements["default"];
}

function updateDepartmentSpecificFields() {
  const departmentId = el("department_id").value;
  const dept = departmentId ? departmentCache.get(parseInt(departmentId)) : null;
  
  const requirements = dept ? getPolicyRequirements(dept.attendance_policy) : getPolicyRequirements("default");
  
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
  el("weekly_rest_day").value = employee.weekly_rest_day || "";
  updateDepartmentSpecificFields();
  
  const collapseEl = document.getElementById('employeeFormCollapse');
  if (collapseEl) {
      const bsCollapse = new bootstrap.Collapse(collapseEl, { toggle: false });
      bsCollapse.show();
      window.scrollTo({ top: 0, behavior: 'smooth' });
  }
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
              
              const collapseEl = document.getElementById('employeeFormCollapse');
              if (collapseEl) {
                  const bsCollapse = bootstrap.Collapse.getInstance(collapseEl);
                  if (bsCollapse) bsCollapse.hide();
              }
          } catch (error) {
              showAlert("employeeAlert", error.message);
          }
      });
    }
    
    const uploadForm = document.getElementById("uploadDocumentForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", async (event) => {
          event.preventDefault();
          
          if (!selectedEmployeeId) {
            showAlert("employeeAlert", "اختر موظفًا أولاً قبل رفع مستند.");
            return;
          }

          const fileInput = el("docFile");
          if (!fileInput.files || !fileInput.files[0]) {
            showAlert("employeeAlert", "اختر ملفًا قبل رفع المستند.");
            return;
          }
          
          const formData = new FormData();
          formData.append("employee_id", selectedEmployeeId);
          formData.append("name", el("docName").value);
          formData.append("notes", el("docNotes").value);
          formData.append("file", fileInput.files[0]);
          
          try {
              const token = getToken();
              const response = await fetch(`/api/employee-documents/`, {
                  method: "POST",
                  headers: {
                      "Authorization": `Bearer ${token}`
                  },
                  body: formData
              });

              if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || "حدث خطأ أثناء رفع المستند.");
              }
              
              uploadForm.reset();
              await loadEmployeeDocuments(selectedEmployeeId);
              showAlert("employeeAlert", "تم رفع المستند بنجاح", "success");
          } catch (error) {
              showAlert("employeeAlert", error.message || "حدث خطأ أثناء رفع المستند");
          }
      });
    }
});
