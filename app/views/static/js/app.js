const apiBase = "";

// Safe element getter - returns dummy object if element not found
function el(id) {
    const element = document.getElementById(id);
    if (element) {
        return element;
    }
    return new Proxy({}, {
        set: () => true,
        get: (target, prop) => {
            if (prop === 'addEventListener') {
                return () => {};
            }
            return '';
        }
    });
}

function getToken() {
    const localToken = localStorage.getItem("attendance_token");
    if (localToken) {
        return localToken;
    }

    const cookieToken = document.cookie
        .split("; ")
        .find((row) => row.startsWith("attendance_token="))
        ?.split("=")[1];

    if (cookieToken) {
        const decodedToken = decodeURIComponent(cookieToken);
        localStorage.setItem("attendance_token", decodedToken);
        return decodedToken;
    }

    return null;
}

function setToken(token) {
    localStorage.setItem("attendance_token", token);
    document.cookie = `attendance_token=${encodeURIComponent(token)}; path=/; SameSite=Lax`;
}

function clearToken() {
    localStorage.removeItem("attendance_token");
    localStorage.removeItem("attendance_user");
    document.cookie = "attendance_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
}

function setUser(user) {
    localStorage.setItem("attendance_user", JSON.stringify(user));
}

function getUser() {
    const user = localStorage.getItem("attendance_user");
    return user ? JSON.parse(user) : null;
}

async function fetchJSON(url, options = {}) {
    const token = getToken();
    const branchId = getCurrentBranchId();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    if (branchId) {
        headers["X-Branch-Id"] = branchId;
    }

    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401 && !url.includes("/api/auth/login")) {
        clearToken();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
        throw new Error("انتهت الجلسة أو يلزم تسجيل الدخول.");
    }
    
    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.blob();

    if (!response.ok) {
        throw new Error(data.detail || "فشل تنفيذ الطلب.");
    }
    return data;
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = "/login";
    }
}

async function hydrateUser() {
    if (!getToken()) {
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
        return null;
    }

    try {
        const user = await fetchJSON("/api/auth/me");
        setUser(user);
        const userNameElement = el("currentUserName");
        if (userNameElement) {
            userNameElement.textContent = user.full_name;
        }
        return user;
    } catch (error) {
        console.error("Error hydrating user:", error);
        clearToken();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
        return null;
    }
}

function showAlert(targetId, message, type = "danger") {
    const container = document.getElementById(targetId);
    if (!container) {
        return;
    }
    // don't render empty/falsy messages (prevents showing silent alerts on auth redirect)
    if (!message) {
        return;
    }
    container.innerHTML = `<div class="alert alert-${type}" role="alert">${message}</div>`;
}

function downloadFile(url) {
    const token = getToken();
    window.open(`${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`, "_blank");
}

function getCurrentBranchId() {
    return localStorage.getItem("attendance_branch_id");
}

function setCurrentBranchId(branchId) {
    localStorage.setItem("attendance_branch_id", String(branchId));
}

function getCurrentBranchName() {
    return localStorage.getItem("attendance_branch_name") || "";
}

function setCurrentBranchName(branchName) {
    localStorage.setItem("attendance_branch_name", branchName);
}

async function loadBranchSelector() {
    const branchSelector = document.getElementById("branchSelector");
    if (!branchSelector) {
        return;
    }

    try {
        const branches = await fetchJSON("/api/branches?all=true");
        branchSelector.innerHTML = "";

        if (!branches || !branches.length) {
            branchSelector.innerHTML = `<option value="">لا توجد فروع</option>`;
            return;
        }

        const currentBranchId = getCurrentBranchId();
        let selectedId = currentBranchId && branches.some((branch) => String(branch.id) === currentBranchId)
            ? currentBranchId
            : String(branches[0].id);

        branches.forEach((branch) => {
            const option = document.createElement("option");
            option.value = branch.id;
            option.textContent = branch.name;
            if (String(branch.id) === selectedId) {
                option.selected = true;
            }
            branchSelector.append(option);
        });

        const selectedBranch = branches.find((branch) => String(branch.id) === selectedId);
        if (selectedBranch) {
            setCurrentBranchId(selectedBranch.id);
            setCurrentBranchName(selectedBranch.name);
            const sidebarBranchNameEl = document.getElementById("sidebarBranchName");
            if (sidebarBranchNameEl) {
                sidebarBranchNameEl.textContent = selectedBranch.name;
            }
        }

        branchSelector.addEventListener("change", (event) => {
            const branchId = event.target.value;
            const branch = branches.find((item) => String(item.id) === branchId);
            if (!branch) {
                return;
            }
            setCurrentBranchId(branch.id);
            setCurrentBranchName(branch.name);
            window.location.reload();
        });
    } catch (error) {
        branchSelector.innerHTML = `<option value="">غير متاح</option>`;
    }
}

let ws;

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/attendance`;
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function () {
        console.log("WebSocket connected");
    };
    
    ws.onmessage = function (event) {
        try {
            const message = JSON.parse(event.data);
            if (message.type === "attendance_log") {
                handleNewAttendanceLog(message.data);
            }
        } catch (error) {
            console.error("Error parsing WebSocket message:", error);
        }
    };
    
    ws.onclose = function () {
        console.log("WebSocket closed, trying to reconnect...");
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = function (error) {
        console.error("WebSocket error:", error);
    };
}

function handleNewAttendanceLog(data) {
    // Show real-time notification
    const notification = document.createElement("div");
    notification.className = "alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3 z-index-3";
    notification.style.minWidth = "300px";
    notification.innerHTML = `
        <i class="bi bi-check-circle-fill me-2"></i>
        ${data.employee_name} checked in at ${new Date(data.check_time).toLocaleTimeString()}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
    
    // Reload page if we are on attendance page
    if (window.location.pathname.includes("attendance") || window.location.pathname === "/") {
        // Optionally refresh data without full reload
        console.log("New attendance log received");
    }
}

async function loadDepartmentsNav() {
    const departmentsNav = document.getElementById("departmentsNav");
    if (!departmentsNav) {
        return;
    }

    try {
        const departments = await fetchJSON("/api/departments");
        departmentsNav.innerHTML = "";

        if (!departments || !departments.length) {
            departmentsNav.innerHTML += `<div class="text-white-50 small mt-2">لا توجد أقسام</div>`;
            return;
        }

        departments.forEach((dept) => {
            const link = document.createElement("a");
            link.href = `/departments/${dept.id}`;
            link.className = "nav-sublink";
            // Check if current page is this department's page
            if (window.location.pathname === `/departments/${dept.id}`) {
                link.classList.add("active");
            }
            link.textContent = dept.name;
            departmentsNav.appendChild(link);
        });
    } catch (error) {
        console.error("Error loading departments nav:", error);
        departmentsNav.innerHTML = `<div class="text-white-50 small">خطأ في تحميل الأقسام</div>`;
    }
}

// Nav toggle functionality
document.addEventListener("click", (event) => {
    const toggleBtn = event.target.closest(".nav-toggle");
    if (toggleBtn) {
        const targetId = toggleBtn.getAttribute("aria-controls");
        const target = document.getElementById(targetId);
        if (target) {
            const isExpanded = toggleBtn.getAttribute("aria-expanded") === "true";
            toggleBtn.setAttribute("aria-expanded", !isExpanded);
            target.hidden = isExpanded;
            if (!isExpanded) {
                // Load departments when expanded
                if (targetId === "departmentsNavContainer" && typeof loadDepartmentsNav === "function") {
                    loadDepartmentsNav();
                }
            }
        }
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadBranchSelector();
    const branchNameEl = document.getElementById("sidebarBranchName");
    if (branchNameEl) {
        branchNameEl.textContent = getCurrentBranchName() || "غير محدد";
    }
    connectWebSocket();
});

document.addEventListener("click", (event) => {
    if (event.target.matches("[data-action='logout']")) {
        clearToken();
        window.location.href = "/";
    }
});
