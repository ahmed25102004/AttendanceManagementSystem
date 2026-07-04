const apiBase = "";

function getToken() {
    return localStorage.getItem("attendance_token");
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
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        // silent handling: clear token and redirect to login without showing alert text
        clearToken();
        if (!window.location.pathname.endsWith("/")) {
            window.location.href = "/";
        }
        // reject with empty message so UI handlers that call showAlert won't display text
        throw new Error("");
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
        window.location.href = "/";
    }
}

async function hydrateUser() {
    if (!getToken()) {
        return null;
    }

    try {
        const user = await fetchJSON("/api/auth/me");
        setUser(user);
        const userNameElement = document.getElementById("currentUserName");
        if (userNameElement) {
            userNameElement.textContent = user.full_name;
        }
        return user;
    } catch (error) {
        console.error(error);
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

async function loadNotifications() {
    const unreadCountEl = document.getElementById("unreadCount");
    const dropdownMenu = document.getElementById("notificationDropdownMenu");
    
    if (!unreadCountEl || !dropdownMenu) {
        return;
    }
    
    try {
        const notifications = await fetchJSON("/api/notifications");
        const unreadNotifications = notifications.filter(n => !n.is_read);
        
        unreadCountEl.textContent = unreadNotifications.length;
        if (unreadNotifications.length === 0) {
            unreadCountEl.style.display = "none";
        } else {
            unreadCountEl.style.display = "block";
        }
        
        if (notifications.length === 0) {
            dropdownMenu.innerHTML = `<li class="p-3 text-center text-muted">لا توجد إشعارات</li>`;
        } else {
            let html = `
                <li><a class="dropdown-item" href="#" onclick="markAllAsRead(event)">تعليم جميع الإشعارات كمقروءة</a></li>
                <li><hr class="dropdown-divider"></li>
            `;
            
            notifications.forEach(notification => {
                html += `
                    <li>
                        <a class="dropdown-item ${!notification.is_read ? 'bg-light fw-semibold' : ''}" href="#" onclick="markNotificationAsRead(event, ${notification.id})">
                            <h6 class="mb-0">${notification.title}</h6>
                            <p class="mb-0 text-muted small">${notification.message}</p>
                            <small class="text-muted">${new Date(notification.created_at).toLocaleString('ar-EG')}</small>
                        </a>
                    </li>
                `;
            });
            
            dropdownMenu.innerHTML = html;
        }
    } catch (error) {
        console.error(error);
    }
}

async function markAllAsRead(event) {
    event.preventDefault();
    try {
        await fetchJSON("/api/notifications/mark-all-read", {
            method: "PUT"
        });
        await loadNotifications();
    } catch (error) {
        console.error(error);
    }
}

async function markNotificationAsRead(event, notificationId) {
    event.preventDefault();
    try {
        await fetchJSON(`/api/notifications/${notificationId}/read`, {
            method: "PUT"
        });
        await loadNotifications();
    } catch (error) {
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();
    await loadNotifications();
    
    // Poll for new notifications every 30 seconds
    setInterval(loadNotifications, 30000);
});

document.addEventListener("click", (event) => {
    if (event.target.matches("[data-action='logout']")) {
        clearToken();
        window.location.href = "/";
    }
});
