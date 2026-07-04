const leaveTypesLabels = {
    sick: "مرضية",
    annual: "سنوية",
    personal: "شخصية",
    maternity: "ولادة",
    paternity: "والدة"
};

const leaveStatusLabels = {
    pending: { label: "قيد المراجعة",
        badge: "warning"
    },
    approved: { label: "مقبول",
        badge: "success"
    },
    rejected: { label: "مرفوض",
        badge: "danger"
    }
};

async function loadMyLeaves() {
    const tbody = document.getElementById("myLeavesTableBody");
    tbody.innerHTML = "";
    
    const leaves = await fetchJSON("/api/leaves/my");
    
    leaves.forEach(leave => {
        const type = leaveTypesLabels[leave.type];
        const status = leaveStatusLabels[leave.status];
        
        tbody.innerHTML += `
            <tr>
                <td>${type}</td>
                <td>${leave.start_date}</td>
                <td>${leave.end_date}</td>
                <td>${leave.reason || "-"}</td>
                <td><span class="badge bg-${status.badge}">${status.label}</span></td>
            </tr>
        `
    })
}

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    const user = await hydrateUser();
    if (!user) return;
    if (user.role !== "employee") {
        window.location.href = "/leaves";
        return;
    }
    
    await loadMyLeaves();
    
    document.getElementById("createLeaveForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const leave = {
            employee_id: user.employee_id,
            type: document.getElementById("createLeaveType").value,
            start_date: document.getElementById("createLeaveStartDate").value,
            end_date: document.getElementById("createLeaveEndDate").value,
            reason: document.getElementById("createLeaveReason").value
        };
        
        await fetchJSON("/api/leaves", {
            method: "POST",
            body: JSON.stringify(leave)
        });
        
        showAlert("myLeavesAlert", "تم تقديم الطلب بنجاح", "success");
        document.getElementById("createLeaveForm").reset();
        await loadMyLeaves();
    });
});
