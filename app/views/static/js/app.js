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

// Since we removed all authentication, just use a dummy token
const DUMMY_TOKEN = "dummy_token_no_auth_needed";

function getToken() {
    let token = localStorage.getItem("attendance_token");
    if (!token) {
        token = DUMMY_TOKEN;
        setToken(token);
    }
    return token;
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
    
    // Removed 401 check since we don't use auth anymore
    
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
    // No auth required anymore
    return;
}

async function hydrateUser() {
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
    const branchStatusText = document.getElementById("branchStatusText");
    if (!branchSelector || !branchStatusText) {
        return;
    }

    try {
        const branches = await fetchJSON("/api/branches?all=true");
        branchSelector.innerHTML = "";

        if (!branches || !branches.length) {
            branchSelector.innerHTML = `<option value="">لا توجد فروع</option>`;
            branchStatusText.textContent = "لا توجد فروع مسجلة.";
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
            branchStatusText.textContent = `الفرع الحالي: ${selectedBranch.name}`;
        }

        branchSelector.addEventListener("change", (event) => {
            const branchId = event.target.value;
            const branch = branches.find((item) => String(item.id) === branchId);
            if (!branch) {
                return;
            }
            setCurrentBranchId(branch.id);
            setCurrentBranchName(branch.name);
            branchStatusText.textContent = `الفرع الحالي: ${branch.name}`;
        });
    } catch (error) {
        branchStatusText.textContent = "غير متاح";
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

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadBranchSelector();
    connectWebSocket();
});

document.addEventListener("click", (event) => {
    if (event.target.matches("[data-action='logout']")) {
        clearToken();
        window.location.href = "/";
    }
});
