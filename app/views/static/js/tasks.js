const tasksCache = [];
const employeesCache = [];
let currentUser = null;

function getStatusBadge(status) {
    const badges = {
        pending: { text: "قيد الانتظار", class: "bg-secondary" },
        in_progress: { text: "قيد التنفيذ", class: "bg-warning" },
        completed: { text: "مكتملة", class: "bg-success" },
        cancelled: { text: "ملغاة", class: "bg-danger" }
    };
    const badge = badges[status] || badges.pending;
    return `<span class="badge ${badge.class}">${badge.text}</span>`;
}

function getPriorityBadge(priority) {
    const badges = {
        low: { text: "منخفضة", class: "bg-info" },
        medium: { text: "متوسطة", class: "bg-warning" },
        high: { text: "عالية", class: "bg-danger" }
    };
    const badge = badges[priority] || badges.medium;
    return `<span class="badge ${badge.class}">${badge.text}</span>`;
}

async function loadEmployees() {
    const employees = await fetchJSON("/api/employees");
    employeesCache.length = 0;
    employeesCache.push(...employees);
    
    const createSelect = document.getElementById("createTaskAssignedTo");
    const editSelect = document.getElementById("editTaskAssignedTo");
    
    createSelect.innerHTML = '<option value="">-- اختر موظف --</option>';
    editSelect.innerHTML = '<option value="">-- اختر موظف --</option>';
    
    employees.forEach(emp => {
        const option = `<option value="${emp.id}">${emp.full_name}</option>`;
        createSelect.innerHTML += option;
        editSelect.innerHTML += option;
    });
}

async function loadTasks() {
    const tasks = await fetchJSON("/api/tasks");
    tasksCache.length = 0;
    tasksCache.push(...tasks);
    renderTasks(tasks);
}

function renderTasks(tasks) {
    const container = document.getElementById("tasksContainer");
    
    if (tasks.length === 0) {
        container.innerHTML = '<div class="text-muted text-center py-4">لا توجد مهام بعد</div>';
        return;
    }
    
    let html = '<div class="row g-3">';
    
    tasks.forEach(task => {
        html += `
            <div class="col-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-body d-flex justify-content-between align-items-start">
                        <div>
                            <div class="d-flex align-items-center gap-2 mb-2">
                                <h5 class="card-title mb-0">${task.title}</h5>
                                ${getStatusBadge(task.status)}
                                ${getPriorityBadge(task.priority)}
                            </div>
                            <p class="card-text text-muted mb-2">
                                ${task.description || "لا يوجد وصف"}
                            </p>
                            <div class="d-flex gap-4 text-muted small">
                                <span>معين لـ: ${task.assigned_to_name || "غير محدد"}</span>
                                ${task.due_date ? `<span>تاريخ الاستحقاق: ${task.due_date}</span>` : ""}
                            </div>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-primary btn-sm" onclick="openEditTaskModal(${task.id})">
                                تعديل
                            </button>
                            ${currentUser.role === "admin" ? `
                                <button class="btn btn-outline-danger btn-sm" onclick="deleteTask(${task.id})">
                                    حذف
                                </button>
                            ` : ""}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function deleteTask(taskId) {
    if (!confirm("هل تريد حذف هذه المهمة؟")) return;
    await fetchJSON(`/api/tasks/${taskId}`, { method: "DELETE" });
    await loadTasks();
    showAlert("tasksAlert", "تم حذف المهمة بنجاح", "success");
}

function openEditTaskModal(taskId) {
    const task = tasksCache.find(t => t.id === taskId);
    if (!task) return;
    
    document.getElementById("editTaskId").value = task.id;
    document.getElementById("editTaskTitle").value = task.title;
    document.getElementById("editTaskDescription").value = task.description || "";
    document.getElementById("editTaskAssignedTo").value = task.assigned_to;
    document.getElementById("editTaskStatus").value = task.status;
    document.getElementById("editTaskPriority").value = task.priority;
    document.getElementById("editTaskDueDate").value = task.due_date || "";
    
    const modal = new bootstrap.Modal(document.getElementById("editTaskModal"));
    modal.show();
}

document.addEventListener("DOMContentLoaded", async () => {
    currentUser = await hydrateUser();
    if (!currentUser) return;
    
    // Only show add task form for admins
    if (currentUser.role === "admin") {
        document.getElementById("showAddTaskBtn").style.display = "block";
    } else {
        document.getElementById("showAddTaskBtn").style.display = "none";
    }
    
    await loadEmployees();
    await loadTasks();
    
    document.getElementById("showAddTask").addEventListener("click", () => {
        document.getElementById("showAddTaskBtn").style.display = "none";
        document.getElementById("addTaskForm").style.display = "block";
    });
    
    document.getElementById("cancelAddTask").addEventListener("click", () => {
        document.getElementById("addTaskForm").style.display = "none";
        document.getElementById("showAddTaskBtn").style.display = "block";
        document.getElementById("createTaskForm").reset();
    });
    
    document.getElementById("createTaskForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            title: document.getElementById("createTaskTitle").value,
            description: document.getElementById("createTaskDescription").value || null,
            assigned_to: parseInt(document.getElementById("createTaskAssignedTo").value, 10),
            priority: document.getElementById("createTaskPriority").value,
            due_date: document.getElementById("createTaskDueDate").value || null
        };
        
        await fetchJSON("/api/tasks", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        
        document.getElementById("createTaskForm").reset();
        document.getElementById("addTaskForm").style.display = "none";
        document.getElementById("showAddTaskBtn").style.display = "block";
        await loadTasks();
        showAlert("tasksAlert", "تم إضافة المهمة بنجاح", "success");
    });
    
    document.getElementById("editTaskForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const taskId = parseInt(document.getElementById("editTaskId").value, 10);
        const payload = {
            title: document.getElementById("editTaskTitle").value,
            description: document.getElementById("editTaskDescription").value || null,
            assigned_to: parseInt(document.getElementById("editTaskAssignedTo").value, 10),
            status: document.getElementById("editTaskStatus").value,
            priority: document.getElementById("editTaskPriority").value,
            due_date: document.getElementById("editTaskDueDate").value || null
        };
        
        await fetchJSON(`/api/tasks/${taskId}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
        
        bootstrap.Modal.getInstance(document.getElementById("editTaskModal")).hide();
        await loadTasks();
        showAlert("tasksAlert", "تم تحديث المهمة بنجاح", "success");
    });
});
