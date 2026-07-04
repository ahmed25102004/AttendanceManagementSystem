const FACE_MODEL_URL = "https://justadudewhohacks.github.io/face-api.js/models";
const maState = {
    stream: null,
    modelsLoaded: false,
    faceRegistered: false,
    busy: false,
    lastAction: { action: null, ts: 0 },
    scanInterval: null,
    location: null,
};

function setBigStatus(text, cls = "") {
    const el = document.getElementById("maBigStatus");
    el.textContent = text;
    el.className = cls;
}

function setTodayFlags(record) {
    document.getElementById("maCheckInStatus").textContent = record?.check_in_time
        ? `مسجل ${new Date(record.check_in_time).toLocaleTimeString("ar-EG")}`
        : "غير مسجل";
    document.getElementById("maCheckOutStatus").textContent = record?.check_out_time
        ? `مسجل ${new Date(record.check_out_time).toLocaleTimeString("ar-EG")}`
        : "غير مسجل";
}

function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            resolve({});
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
            () => resolve({})
        );
    });
}

function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function playSuccessTone() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = 880;
        g.gain.value = 0.05;
        o.connect(g);
        g.connect(ctx.destination);
        o.start();
        setTimeout(() => {
            o.stop();
            ctx.close();
        }, 160);
    } catch (e) {
        // ignore audio errors
    }
}

async function ensureFaceModels() {
    if (maState.modelsLoaded) return;
    if (!window.faceapi) throw new Error("تعذر تحميل مكتبة التعرف على الوجه.");
    await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(FACE_MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(FACE_MODEL_URL),
        faceapi.nets.faceRecognitionNet.loadFromUri(FACE_MODEL_URL),
    ]);
    maState.modelsLoaded = true;
}

async function ensureCamera() {
    if (maState.stream) return;
    const video = document.getElementById("maVideo");
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 320 }, height: { ideal: 240 } }, // Smaller resolution for speed
        audio: false,
    });
    maState.stream = stream;
    video.srcObject = stream;
    await video.play();
}

function stopCamera() {
    if (!maState.stream) return;
    maState.stream.getTracks().forEach((track) => track.stop());
    maState.stream = null;
    const video = document.getElementById("maVideo");
    video.pause();
    video.srcObject = null;
    if (maState.scanInterval) {
        clearInterval(maState.scanInterval);
        maState.scanInterval = null;
    }
}

async function detectDescriptor() {
    const video = document.getElementById("maVideo");
    const detection = await faceapi
        .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 160, scoreThreshold: 0.3 })) // Smaller input, lower threshold for speed
        .withFaceLandmarks()
        .withFaceDescriptor();

    if (!detection) {
        throw new Error("لم يتم التعرف على وجه واضح.");
    }

    return Array.from(detection.descriptor);
}

async function loadToday() {
    try {
        const rec = await fetchJSON("/api/attendance/self/today");
        setTodayFlags(rec);
    } catch (e) {
        console.warn(e.message);
    }
}

async function loadFaceStatus() {
    try {
        const st = await fetchJSON("/api/attendance/self/face/status");
        maState.faceRegistered = st.face_registered;
    } catch (e) {
        console.warn(e.message);
    }
}

async function registerFlow() {
    try {
        await ensureFaceModels();
        await ensureCamera();
        setBigStatus("التقاط 3 صور للتسجيل...");
        const descriptors = [];
        for (let i = 0; i < 3; i += 1) {
            descriptors.push(await detectDescriptor());
            await wait(700);
        }
        await fetchJSON("/api/attendance/self/face/register", {
            method: "POST",
            body: JSON.stringify({ descriptors }),
        });
        setBigStatus("تم حفظ بصمة الوجه", "text-success");
        maState.faceRegistered = true;
        playSuccessTone();
        await loadToday();
    } catch (e) {
        setBigStatus(e.message, "text-danger");
    }
}

async function scanOnce() {
    if (maState.busy) return;
    maState.busy = true;
    try {
        await ensureFaceModels();
        await ensureCamera();
        setBigStatus("جاري التحقق من الوجه...");
        const descriptor = await detectDescriptor();

        const payload = { ...maState.location, descriptor };
        const res = await fetchJSON("/api/attendance/self/face/scan", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        setBigStatus(res.message, res.action === "check_in" || res.action === "check_out" ? "text-success" : "");
        if (res.record) setTodayFlags(res.record);

        if (res.action === "check_in" || res.action === "check_out") {
            const now = Date.now();
            if (maState.lastAction.action !== res.action || now - maState.lastAction.ts >= 30000) {
                maState.lastAction = { action: res.action, ts: now };
                playSuccessTone();
            }
            stopCamera();
        }
    } catch (e) {
        setBigStatus(e.message, "text-danger");
    } finally {
        maState.busy = false;
    }
}

async function manualCheckIn() {
    try {
        const location = await getCurrentLocation();
        const record = await fetchJSON("/api/attendance/self/check-in", {
            method: "POST",
            body: JSON.stringify({ ...location }),
        });
        setBigStatus("تم تسجيل الحضور بنجاح!", "text-success");
        setTodayFlags(record);
        playSuccessTone();
    } catch (e) {
        setBigStatus(e.message, "text-danger");
    }
}

async function manualCheckOut() {
    try {
        const location = await getCurrentLocation();
        const record = await fetchJSON("/api/attendance/self/check-out", {
            method: "POST",
            body: JSON.stringify({ ...location }),
        });
        setBigStatus("تم تسجيل الانصراف بنجاح!", "text-success");
        setTodayFlags(record);
        playSuccessTone();
    } catch (e) {
        setBigStatus(e.message, "text-danger");
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();
    const user = await hydrateUser();
    if (!user) return;

    await Promise.all([loadToday(), loadFaceStatus()]);

    document.getElementById("maOpenBtn").addEventListener("click", async () => {
        setBigStatus("فتح الكاميرا وتحديد الموقع...");
        try {
            // Get location once when camera starts
            maState.location = await getCurrentLocation();
            
            await ensureFaceModels();
            await ensureCamera();

            if (!maState.faceRegistered) {
                await registerFlow();
            } else {
                // Auto scan every 4 seconds (reduced load)
                setBigStatus("الكاميرا تعمل. وجّه وجهك للكاميرا...");
                maState.scanInterval = setInterval(() => {
                    if (!maState.stream) {
                        clearInterval(maState.scanInterval);
                        maState.scanInterval = null;
                        return;
                    }
                    scanOnce();
                }, 4000);
            }
        } catch (e) {
            setBigStatus(e.message, "text-danger");
        }
    });

    document.getElementById("maStopBtn").addEventListener("click", () => {
        stopCamera();
        setBigStatus("الكاميرا مغلقة");
    });

    document.getElementById("maManualCheckInBtn").addEventListener("click", manualCheckIn);
    document.getElementById("maManualCheckOutBtn").addEventListener("click", manualCheckOut);
});
