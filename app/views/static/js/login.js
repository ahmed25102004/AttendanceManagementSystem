document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    if (!loginForm) {
        return;
    }

    if (getToken()) {
        hydrateUser().then((user) => {
            if (user) {
                window.location.href = user.role === "employee" ? "/my-attendance" : "/dashboard";
            }
        });
        return;
    }

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
        };

        try {
            const data = await fetchJSON("/api/auth/login", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            setToken(data.access_token);
            const user = await hydrateUser();
            window.location.href = user?.role === "employee" ? "/my-attendance" : "/dashboard";
        } catch (error) {
            showAlert("loginAlert", error.message);
        }
    });

});
