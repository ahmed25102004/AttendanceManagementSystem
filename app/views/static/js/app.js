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

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadBranchSelector();
});

document.addEventListener("click", (event) => {
    if (event.target.matches("[data-action='logout']")) {
        clearToken();
        window.location.href = "/";
    }
});
