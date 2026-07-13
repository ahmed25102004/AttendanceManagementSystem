const deviceCache = new Map();
const branchCache = new Map();

function showDeviceAlert(message, type = "danger") {
    const element = document.getElementById("deviceAlert");
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
    const selectEl = document.getElementById("deviceBranchId");
    if (!selectEl) return;
    selectEl.innerHTML = "<option value=''>-- اختر الفرع --</option>";
    branchCache.clear();
    branches.forEach((branch) => {
        branchCache.set(branch.id, branch);
        const option = document.createElement("option");
        option.value = branch.id;
        option.textContent = branch.name;
        selectEl.appendChild(option);
    });
}

async function loadDevices() {
        const devices = await fetchJSON("/api/devices?all=true");
        const tbody = document.getElementById("deviceTableBody");
        if (!tbody) return;
        tbody.innerHTML = "";
        deviceCache.clear();

        devices.forEach((device) => {
            deviceCache.set(device.id, device);
            const branch = branchCache.get(device.branch_id);
            tbody.innerHTML += `
                <tr>
                    <td>${device.device_name}</td>
                    <td>${branch ? branch.name : "-"}</td>
                    <td>
                        <span class="badge bg-${device.status === 'Online' ? 'success' : 'secondary'}">
                            ${device.status}
                        </span>
                    </td>
                    <td>${device.last_seen ? new Date(device.last_seen).toLocaleString('ar-EG') : "-"}</td>
                    <td>${device.last_sync ? new Date(device.last_sync).toLocaleString('ar-EG') : "-"}</td>
                    <td>${device.log_count || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-info ms-2" onclick="testDevice(${device.id})">اختبار الاتصال</button>
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="editDevice(${device.id})">تعديل</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteDevice(${device.id})">حذف</button>
                    </td>
                </tr>
            `;
        });
    }

function resetDeviceForm() {
    const form = document.getElementById("deviceForm");
    if (form) form.reset();
    el("deviceId").value = "";
    el("deviceIsActive").checked = true;
}

function editDevice(deviceId) {
    const device = deviceCache.get(deviceId);
    if (!device) {
        showDeviceAlert("تعذر تحميل بيانات الجهاز.");
        return;
    }

    el("deviceId").value = device.id;
    el("deviceName").value = device.device_name;
    el("deviceCode").value = device.device_code;
    el("serialNumber").value = device.serial_number || "";
    el("deviceBranchId").value = device.branch_id;
    el("ipAddress").value = device.ip_address || "";
    el("devicePort").value = device.port || "";
    el("deviceProtocol").value = device.protocol;
    el("firmwareVersion").value = device.firmware_version || "";
    el("deviceIsActive").checked = device.is_active;
}

async function deleteDevice(deviceId) {
    if (!confirm("هل تريد حذف هذا الجهاز؟")) {
        return;
    }

    try {
        await fetchJSON(`/api/devices/${deviceId}`, { method: "DELETE" });
        await loadDevices();
        resetDeviceForm();
        showDeviceAlert("تم حذف الجهاز بنجاح.", "success");
    } catch (error) {
        showDeviceAlert(error.message);
    }
}

async function testDevice(deviceId) {
    try {
        const result = await fetchJSON(`/api/devices/${deviceId}/test`, { method: "POST" });
        showDeviceAlert(result.message, "success");
    } catch (error) {
        showDeviceAlert(error.message);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const user = await hydrateUser();
    try {
        await loadBranchSelector();
        await loadBranches();
        await loadDevices();
    } catch (error) {
        showDeviceAlert(error.message);
    }

    const form = document.getElementById("deviceForm");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const deviceId = el("deviceId").value;

            const payload = {
                device_name: el("deviceName").value.trim(),
                device_code: el("deviceCode").value.trim(),
                serial_number: el("serialNumber").value.trim() || null,
                branch_id: parseInt(el("deviceBranchId").value) || null,
                ip_address: el("ipAddress").value.trim() || null,
                port: el("devicePort").value ? parseInt(el("devicePort").value) : null,
                protocol: el("deviceProtocol").value,
                firmware_version: el("firmwareVersion").value.trim() || null,
                is_active: el("deviceIsActive").checked,
            };

            const method = deviceId ? "PUT" : "POST";
            const url = deviceId ? `/api/devices/${deviceId}` : "/api/devices";

            try {
                await fetchJSON(url, {
                    method,
                    body: JSON.stringify(payload),
                });
                resetDeviceForm();
                await loadDevices();
                showDeviceAlert(deviceId ? "تم تحديث بيانات الجهاز بنجاح." : "تم إضافة الجهاز بنجاح.", "success");
            } catch (error) {
                showDeviceAlert(error.message);
            }
        });
    }
});
