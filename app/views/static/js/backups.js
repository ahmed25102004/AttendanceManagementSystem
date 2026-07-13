document.addEventListener("DOMContentLoaded", async () => {
    await hydrateUser();

    async function loadBackups() {
        const backups = await fetchJSON("/api/backups");
        const tableBody = document.getElementById("backupsTableBody");
        
        if (backups.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">لا توجد نسخ احتياطية</td></tr>';
            return;
        }

        tableBody.innerHTML = backups.map(backup => `
            <tr>
                <td>${escapeHtml(backup.name)}</td>
                <td>${new Date(backup.created_at).toLocaleString('ar-SA')}</td>
                <td>${formatFileSize(backup.size)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="downloadBackup('${escapeHtml(backup.name)}')">تحميل</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteBackup('${escapeHtml(backup.name)}')">حذف</button>
                </td>
            </tr>
        `).join('');
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        else return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    window.downloadBackup = function(filename) {
        window.location.href = `/api/backups/download/${encodeURIComponent(filename)}`;
    };

    window.deleteBackup = async function(filename) {
        if (!confirm('هل أنت متأكد من حذف هذه النسخة الاحتياطية؟')) return;
        
        try {
            await fetchJSON(`/api/backups/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            showAlert("backupsAlert", "تم حذف النسخة الاحتياطية بنجاح.", "success");
            await loadBackups();
        } catch (error) {
            showAlert("backupsAlert", error.message);
        }
    };

    // Load backups initially
    try {
        await loadBackups();
    } catch (error) {
        showAlert("backupsAlert", error.message);
    }

    // Create backup
    document.getElementById("createBackupBtn").addEventListener("click", async () => {
        try {
            await fetchJSON("/api/backups", {
                method: "POST"
            });
            showAlert("backupsAlert", "تم إنشاء النسخة الاحتياطية بنجاح.", "success");
            await loadBackups();
        } catch (error) {
            showAlert("backupsAlert", error.message);
        }
    });

    // Restore backup
    document.getElementById("restoreBackupBtn").addEventListener("click", async () => {
        const fileInput = document.getElementById("restoreFileInput");
        const file = fileInput.files[0];
        
        if (!file) {
            showAlert("backupsAlert", "يرجى اختيار ملف النسخة الاحتياطية أولاً.");
            return;
        }

        if (!confirm('هل أنت متأكد من استعادة النسخة الاحتياطية؟ سيتم استبدال جميع البيانات الحالية!')) return;

        try {
            const formData = new FormData();
            formData.append("file", file);
            
            await fetch("/api/backups/restore", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${getToken()}`
                },
                body: formData
            });
            
            showAlert("backupsAlert", "تم استعادة النسخة الاحتياطية بنجاح.", "success");
            await loadBackups();
        } catch (error) {
            showAlert("backupsAlert", error.message);
        }
    });
});
