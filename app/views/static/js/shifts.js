const shiftsCache = [];

async function loadShifts() {
    const tbody = document.getElementById("shiftsTableBody");
    tbody.innerHTML = "";
    
    const shifts = await fetchJSON("/api/shifts");
    shiftsCache = shifts;
    
    shifts.forEach((shift) => {
        tbody.innerHTML += `
            <tr>
                <td>${shift.name}</td>
                <td>${shift.start_time}</td>
                <td>${shift.end_time}</td>
                <td>${shift.grace_period_minutes} دقيقة</td>
                <td>
                    <span class="badge bg-${shift.is_active ? 'success' : 'secondary'}">
                        ${shift.is_active ? 'فعّال' : 'غير فعّال'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="openEditModal(${shift.id})">تعديل</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteShift(${shift.id})">حذف</button>
                </td>
            </tr>
        `;
    });
}

async function deleteShift(shiftId) {
    if (!confirm("هل تريد حذف هذه الوردية؟")) return;
    
    await fetchJSON(`/api/shifts/${shiftId}`, { method: "DELETE" });
    await loadShifts();
    showAlert("shiftsAlert", "تم الحذف بنجاح", "success");
}

function openEditModal(shiftId) {
    const shift = shiftsCache.find(x => x.id === shiftId);
    if (!shift) return;
    
    document.getElementById("editShiftId").value = shiftId;
    document.getElementById("editShiftName").value = shift.name;
    document.getElementById("editShiftStartTime").value = shift.start_time;
    document.getElementById("editShiftEndTime").value = shift.end_time;
    document.getElementById("editShiftGracePeriod").value = shift.grace_period_minutes;
    document.getElementById("editShiftIsActive").checked = shift.is_active;
    
    const modal = new bootstrap.Modal(document.getElementById("editShiftModal"));
    modal.show();
}

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    await hydrateUser();
    await loadShifts();
    
    document.getElementById("createShiftForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            name: document.getElementById("createShiftName").value,
            start_time: document.getElementById("createShiftStartTime").value,
            end_time: document.getElementById("createShiftEndTime").value,
            grace_period_minutes: parseInt(document.getElementById("createShiftGracePeriod").value, 10),
            is_active: document.getElementById("createShiftIsActive").checked
        };
        
        await fetchJSON("/api/shifts", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        
        document.getElementById("createShiftForm").reset();
        await loadShifts();
        showAlert("shiftsAlert", "تم إضافة الوردية بنجاح", "success");
    });
    
    document.getElementById("editShiftForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const shiftId = parseInt(document.getElementById("editShiftId").value, 10);
        const payload = {
            name: document.getElementById("editShiftName").value,
            start_time: document.getElementById("editShiftStartTime").value,
            end_time: document.getElementById("editShiftEndTime").value,
            grace_period_minutes: parseInt(document.getElementById("editShiftGracePeriod").value, 10),
            is_active: document.getElementById("editShiftIsActive").checked
        };
        
        await fetchJSON(`/api/shifts/${shiftId}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
        
        bootstrap.Modal.getInstance(document.getElementById("editShiftModal")).hide();
        await loadShifts();
        showAlert("shiftsAlert", "تم تحديث الوردية بنجاح", "success");
    });
});
