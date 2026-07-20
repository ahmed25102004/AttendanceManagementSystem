document.addEventListener("DOMContentLoaded", async () => {
    const existingToken = getToken();
    if (existingToken) {
        const user = await hydrateUser();
        if (user) {
            window.location.href = "/";
            return;
        }
    }

    const form = document.getElementById("loginForm");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const username = document.getElementById("username")?.value?.trim();
        const password = document.getElementById("password")?.value ?? "";

        try {
            const response = await fetchJSON("/api/auth/login", {
                method: "POST",
                headers: {},
                body: JSON.stringify({ username, password }),
            });

            setToken(response.access_token);
            await hydrateUser();
            window.location.href = "/";
        } catch (error) {
            showAlert("loginAlert", error.message || "فشل تسجيل الدخول.");
        }
    });
});
