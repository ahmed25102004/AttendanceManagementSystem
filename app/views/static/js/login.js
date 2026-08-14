document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const username = document.getElementById("username")?.value?.trim();
        const password = document.getElementById("password")?.value ?? "";
        const submitBtn = document.getElementById("loginSubmitBtn");

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm ms-2"></span> جارٍ تسجيل الدخول...';
            }

            const response = await fetchJSON("/api/auth/login", {
                method: "POST",
                headers: {},
                body: JSON.stringify({ username, password }),
            });

            setToken(response.access_token);
            window.location.href = "/";
        } catch (error) {
            showAlert("loginAlert", error.message || "فشل تسجيل الدخول.");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span id="btnText">تسجيل الدخول</span><i class="bi bi-arrow-left ms-2" id="btnIcon"></i>';
            }
        }
    });
});
