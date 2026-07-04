const FACE_MODEL_URL = "https://justadudewhohacks.github.io/face-api.js/models";
const scanState = {
    stream: null,
    modelsLoaded: false,
    running: false,
    busy: false,
    faceRegistered: false,
    timerId: null,
    lastAction: { action: null, ts: 0 },
};

function formatDateTime(value) {
    return value ? new Date(value).toLocaleString("ar-EG") : "-";
}

function formatTimeValue(value) {
    if (!value) {
        return "-";
    }
    return value.slice(0, 5);
}

function renderAttendanceStatus(record) {
    document.getElementById("portalTodayDate").textContent = record?.attendance_date || new Date().toLocaleDateString("ar-EG");
    document.getElementById("portalCheckInTime").textContent = formatDateTime(record?.check_in_time);
    document.getElementById("portalCheckOutTime").textContent = formatDateTime(record?.check_out_time);
    document.getElementById("portalWorkingHours").textContent = record ? `${record.working_hours} ساعة` : "-";
    document.getElementById("portalLateStatus").textContent = record ? (record.is_late ? "متأخر" : "في الموعد") : "-";
}

function setPortalMessage(message) {
    document.getElementById("portalScanMessage").textContent = message;
}

function setScanBadge(label, active = false) {
    const badge = document.getElementById("portalScanBadge");
    badge.textContent = label;
    badge.className = `badge ${active ? "text-bg-success" : "text-bg-light"}`;
}

function updateToggleButton() {
    document.getElementById("toggleAutoScanButton").textContent = scanState.running
        ? "إيقاف التعرف التلقائي"
        : "بدء التعرف التلقائي";
}

function updateFaceRegistrationState(status) {
    scanState.faceRegistered = status.face_registered;
    document.getElementById("portalFaceStatus").textContent = status.face_registered
        ? `مسجل منذ ${formatDateTime(status.face_registered_at)}`
        : "غير مسجل";
    document.getElementById("portalCheckInWindow").textContent =
        `${formatTimeValue(status.check_in_open_time)} - ${formatTimeValue(status.check_in_close_time)}`;
    document.getElementById("portalCheckOutWindow").textContent =
        `${formatTimeValue(status.check_out_open_time)} - ${formatTimeValue(status.check_out_close_time)}`;
}

function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("المتصفح الحالي لا يدعم الحصول على الموقع."));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy_meters: position.coords.accuracy,
                });
            },
            () => reject(new Error("تعذر الوصول إلى موقع الجهاز. يرجى السماح بالموقع وإعادة المحاولة.")),
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    });
}

function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function ensureFaceModels() {
    if (scanState.modelsLoaded) {
        return;
    }
    if (!window.faceapi) {
        throw new Error("تعذر تحميل مكتبة التعرف على الوجه.");
    }

    await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(FACE_MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(FACE_MODEL_URL),
        faceapi.nets.faceRecognitionNet.loadFromUri(FACE_MODEL_URL),
    ]);
    scanState.modelsLoaded = true;
}

async function ensureCameraStream() {
    if (scanState.stream) {
        return;
    }
    const video = document.getElementById("faceVideo");
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
    });
    scanState.stream = stream;
    video.srcObject = stream;
    await video.play();
}

function stopCameraStream() {
    if (!scanState.stream) {
        return;
    }
    scanState.stream.getTracks().forEach((track) => track.stop());
    scanState.stream = null;
}

async function detectFaceDescriptor() {
    const video = document.getElementById("faceVideo");
    const detection = await faceapi
        .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 }))
        .withFaceLandmarks()
        .withFaceDescriptor();
    if (!detection) {
        throw new Error("لم يتم التعرف على وجه واضح أمام الكاميرا.");
    }
    return Array.from(detection.descriptor);
}

async function captureRegistrationSamples() {
    const descriptors = [];
    for (let index = 0; index < 3; index += 1) {
        setPortalMessage(`يتم التقاط عينة الوجه ${index + 1} من 3. ابقَ ثابتًا أمام الكاميرا.`);
        descriptors.push(await detectFaceDescriptor());
        await wait(800);
    }
    return descriptors;
}

async function loadTodayStatus() {
    const record = await fetchJSON("/api/attendance/self/today");
    renderAttendanceStatus(record);
}

async function loadFaceStatus() {
    const status = await fetchJSON("/api/attendance/self/face/status");
    updateFaceRegistrationState(status);
}

async function registerFace() {
    try {
        await ensureFaceModels();
        await ensureCameraStream();
        const descriptors = await captureRegistrationSamples();
        const response = await fetchJSON("/api/attendance/self/face/register", {
            method: "POST",
            body: JSON.stringify({ descriptors }),
        });
        scanState.faceRegistered = response.face_registered;
        await loadFaceStatus();
        showAlert("employeePortalAlert", "تم حفظ بصمة الوجه بنجاح. يمكنك بدء التعرف التلقائي الآن.", "success");
        setPortalMessage("تم تسجيل بصمة الوجه بنجاح.");
    } catch (error) {
        showAlert("employeePortalAlert", error.message);
        setPortalMessage(error.message);
    }
}

async function performFaceScan() {
    if (!scanState.running || scanState.busy) {
        return;
    }

    scanState.busy = true;
    try {
        const [locationPayload, descriptor] = await Promise.all([getCurrentLocation(), detectFaceDescriptor()]);
        const response = await fetchJSON("/api/attendance/self/face/scan", {
            method: "POST",
            body: JSON.stringify({ ...locationPayload, descriptor }),
        });
        setPortalMessage(response.message);
        if (response.record) {
            renderAttendanceStatus(response.record);
        }
        const now = Date.now();
        if (response.action === "check_in" || response.action === "check_out") {
            if (scanState.lastAction.action === response.action && now - scanState.lastAction.ts < 30000) {
                // ignore duplicate
            } else {
                scanState.lastAction = { action: response.action, ts: now };
                showAlert("employeePortalAlert", response.message, "success");
                await loadTodayStatus();
                // play short tone and stop camera for better UX
                try { const actx = new (window.AudioContext || window.webkitAudioContext)(); const o = actx.createOscillator(); const g = actx.createGain(); o.type='sine'; o.frequency.value=880; g.gain.value=0.03; o.connect(g); g.connect(actx.destination); o.start(); setTimeout(()=>{o.stop(); actx.close();},160); } catch(_){}
                stopAutoScan();
            }
        }
        if (response.action === "mismatch") {
            setScanBadge("مطابقة فاشلة", false);
        } else {
            setScanBadge("التعرف نشط", true);
        }
    } catch (error) {
        showAlert("employeePortalAlert", error.message);
        setPortalMessage(error.message);
        stopAutoScan();
    } finally {
        scanState.busy = false;
    }
}

async function startAutoScan() {
    if (!scanState.faceRegistered) {
        showAlert("employeePortalAlert", "يجب تسجيل بصمة الوجه أولًا.");
        setPortalMessage("سجل بصمة الوجه أولًا قبل بدء التعرف التلقائي.");
        return;
    }

    try {
        await ensureFaceModels();
        await ensureCameraStream();
        scanState.running = true;
        updateToggleButton();
        setScanBadge("التعرف نشط", true);
        setPortalMessage("الكاميرا تعمل الآن. سيتم التسجيل تلقائيًا عند مطابقة الوجه ودخول الوقت المناسب.");
        await performFaceScan();
        scanState.timerId = window.setInterval(performFaceScan, 6000);
    } catch (error) {
        showAlert("employeePortalAlert", error.message);
        setPortalMessage(error.message);
        stopAutoScan();
    }
}

function stopAutoScan() {
    scanState.running = false;
    if (scanState.timerId) {
        window.clearInterval(scanState.timerId);
        scanState.timerId = null;
    }
    stopCameraStream();
    updateToggleButton();
    setScanBadge("غير نشط", false);
}

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    const user = await hydrateUser();
    if (!user) {
        return;
    }

    if (user.role !== "employee") {
        window.location.href = "/dashboard";
        return;
    }

    document.getElementById("employeePortalName").textContent = user.full_name;

    try {
        await Promise.all([loadTodayStatus(), loadFaceStatus()]);
    } catch (error) {
        showAlert("employeePortalAlert", error.message);
        setPortalMessage(error.message);
    }

    document.getElementById("registerFaceButton").addEventListener("click", registerFace);
    document.getElementById("toggleAutoScanButton").addEventListener("click", async () => {
        if (scanState.running) {
            stopAutoScan();
            setPortalMessage("تم إيقاف التعرف التلقائي.");
            return;
        }
        await startAutoScan();
    });

    window.addEventListener("beforeunload", () => {
        stopAutoScan();
    });
});
