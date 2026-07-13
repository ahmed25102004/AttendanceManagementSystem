const branchCache = new Map();

function showBranchAlert(message, type = "danger") {
    const element = document.getElementById("branchAlert");
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
    const tbody = document.getElementById("branchTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    branchCache.clear();

    branches.forEach((branch) => {
        branchCache.set(branch.id, branch);
        tbody.innerHTML += `
            <tr>
                <td>${branch.name}</td>
                <td>${branch.description || "-"}</td>
                <td>
                    <span class="badge bg-${branch.is_active ? "success" : "secondary"}">
                        ${branch.is_active ? "فعال" : "غير فعال"}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-info ms-2" onclick="viewBranchDashboard(${branch.id})">لوحة</button>
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="editBranch(${branch.id})">تعديل</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteBranch(${branch.id})">حذف</button>
                </td>
            </tr>
        `;
    });
}

function resetBranchForm() {
    const form = document.getElementById("branchForm");
    if (form) form.reset();
    el("branchId").value = "";
    el("branchIsActive").checked = true;
    el("checkInOpenTime").value = "08:00";
    el("checkInCloseTime").value = "11:00";
    el("checkOutOpenTime").value = "16:00";
    el("checkOutCloseTime").value = "22:00";
    el("allowedLateMinutes").value = "15";
}

function formatTimeForInput(timeStr) {
    if (!timeStr) return "";
    const parts = timeStr.split(":");
    if (parts.length >= 2) {
        return `${parts[0]}:${parts[1]}`;
    }
    return timeStr;
}

function editBranch(branchId) {
    const branch = branchCache.get(branchId);
    if (!branch) {
        showBranchAlert("تعذر تحميل بيانات الفرع.");
        return;
    }

    el("branchId").value = branch.id;
    el("branchName").value = branch.name;
    el("branchDescription").value = branch.description || "";
    el("checkInOpenTime").value = formatTimeForInput(branch.check_in_open_time);
    el("checkInCloseTime").value = formatTimeForInput(branch.check_in_close_time);
    el("checkOutOpenTime").value = formatTimeForInput(branch.check_out_open_time);
    el("checkOutCloseTime").value = formatTimeForInput(branch.check_out_close_time);
    el("allowedLateMinutes").value = branch.allowed_late_minutes;
    el("branchIsActive").checked = branch.is_active;
}

function viewBranchDashboard(branchId) {
    window.location.href = `/branches/${branchId}`;
}

async function deleteBranch(branchId) {
    if (!confirm("هل تريد حذف هذا الفرع؟")) {
        return;
    }

    try {
        await fetchJSON(`/api/branches/${branchId}`, { method: "DELETE" });
        await loadBranches();
        resetBranchForm();
        // Reload branch selector in header
        if (typeof loadBranchSelector === "function") {
            await loadBranchSelector();
        }
        showBranchAlert("تم حذف الفرع بنجاح.", "success");
    } catch (error) {
        showBranchAlert(error.message);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const user = await hydrateUser();
    if (!user) return;

    try {
        await loadBranches();
    } catch (error) {
        console.error("Error loading branches:", error);
        showBranchAlert(error.message);
    }

    const form = document.getElementById("branchForm");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const branchId = el("branchId").value;

            const payload = {
                name: el("branchName").value.trim(),
                description: el("branchDescription").value.trim() || null,
                check_in_open_time: el("checkInOpenTime").value,
                check_in_close_time: el("checkInCloseTime").value,
                check_out_open_time: el("checkOutOpenTime").value,
                check_out_close_time: el("checkOutCloseTime").value,
                allowed_late_minutes: parseInt(el("allowedLateMinutes").value),
                is_active: el("branchIsActive").checked,
            };

            const method = branchId ? "PUT" : "POST";
            const url = branchId ? `/api/branches/${branchId}` : "/api/branches";

            try {
                await fetchJSON(url, {
                    method,
                    body: JSON.stringify(payload),
                });
                resetBranchForm();
                await loadBranches();
                // Reload branch selector in header to include new branch
                if (typeof loadBranchSelector === "function") {
                    await loadBranchSelector();
                }
                showBranchAlert(branchId ? "تم تحديث بيانات الفرع بنجاح." : "تم إضافة الفرع بنجاح.", "success");
            } catch (error) {
                console.error("Error submitting branch:", error);
                showBranchAlert(error.message);
            }
        });
    }
});
