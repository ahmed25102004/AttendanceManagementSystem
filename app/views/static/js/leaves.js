const leavesCache = [];

function getStatusLabel(status) {
    const statusMap = {
        pending: { label: "قيد المراجعة",
            badge: "warning"
        },
        approved: { label: "مقبول",
            badge: "success"
        },
        rejected: { label: "مرفوض",
            badge: "danger"
        }
    }
    return statusMap[status] || statusMap.pending
}

function getLeaveTypeLabel(type) {
    const typeMap = {
        sick: "مرضية",
        annual: "سنوية",
        personal: "شخصية",
        maternity: "ولادة",
        paternity: "والدة"
    }
    return typeMap[type] || type;
}

async function loadLeaves() {
    const tbody = document.getElementById("leavesTableBody");
    tbody.innerHTML = "";
    
    const leaves = await fetchJSON("/api/leaves");
    leavesCache = leaves;
    
    leaves.forEach((leave) => {
        const status = getStatusLabel(leave.status);
        const type = getLeaveTypeLabel(leave.type);
        
        tbody.innerHTML += `
            <tr>
                <td>${leave.employee_name}</td>
                <td>${type}</td>
                <td>${leave.start_date}</td>
                <td>${leave.end_date}</td>
                <td>${leave.reason || "-"}</td>
                <td><span class="badge bg-${status.badge}">${status.label}</span></td>
                <td>
                    ${leave.status === "pending" ? `
                    <button class="btn btn-sm btn-outline-primary" onclick="openEditModal(${leave.id})">تعديل</button>
                    ` : ""}
                </td>
            </tr>
        `
    })
}

function openEditModal(leaveId) {
    const leave = leavesCache.find(x => x.id === leaveId);
    if (!leave) return;
    
    document.getElementById("editLeaveId").value = leaveId;
    document.getElementById("editLeaveStatus").value = leave.status;
    
    const modal = new bootstrap.Modal(document.getElementById("editLeaveModal"));
    modal.show();
}

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    const user = await hydrateUser();
    if (!user) return;
    if (user.role !== "admin") {
        window.location.href = "/my-leaves";
        return;
    }
    
    await loadLeaves();
    
    document.getElementById("editLeaveForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const leaveId = parseInt(document.getElementById("editLeaveId").value);
        const status = document.getElementById("editLeaveStatus").value;
        
        await fetchJSON(`/api/leaves/${leaveId}`, {
            method: "PUT",
            body: JSON.stringify({ status })
        });
        
        bootstrap.Modal.getInstance(document.getElementById("editLeaveModal")).hide();
        await loadLeaves();
        showAlert("leavesAlert", "تم تحديث الحالة بنجاح", "success");
    });
});
