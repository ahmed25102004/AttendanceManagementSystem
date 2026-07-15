
document.addEventListener('DOMContentLoaded', () => {
    // Get employee ID from the path or a hidden field
    const path = window.location.pathname;
    const employeeId = path.split('/').pop();
    
    let weeklyChart = null;
    let pieChart = null;

    // Load initial data
    loadEmployeeData();
    loadStats();
    loadAttendanceLogs();

    // Date filter buttons
    document.getElementById('btn-today').addEventListener('click', () => {
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('start-date').value = today;
        document.getElementById('end-date').value = today;
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-yesterday').addEventListener('click', () => {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yStr = yesterday.toISOString().split('T')[0];
        document.getElementById('start-date').value = yStr;
        document.getElementById('end-date').value = yStr;
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-this-week').addEventListener('click', () => {
        const today = new Date();
        const day = today.getDay();
        const diff = today.getDate() - day + (day === 0 ? -6 : 1);
        const startOfWeek = new Date(today.setDate(diff));
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(endOfWeek.getDate() + 6);
        
        document.getElementById('start-date').value = startOfWeek.toISOString().split('T')[0];
        document.getElementById('end-date').value = endOfWeek.toISOString().split('T')[0];
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-last-week').addEventListener('click', () => {
        const today = new Date();
        const day = today.getDay();
        const diff = today.getDate() - day + (day === 0 ? -6 : 1);
        const startOfLastWeek = new Date(today.setDate(diff - 7));
        const endOfLastWeek = new Date(startOfLastWeek);
        endOfLastWeek.setDate(endOfLastWeek.getDate() + 6);
        
        document.getElementById('start-date').value = startOfLastWeek.toISOString().split('T')[0];
        document.getElementById('end-date').value = endOfLastWeek.toISOString().split('T')[0];
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-this-month').addEventListener('click', () => {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        
        document.getElementById('start-date').value = firstDay.toISOString().split('T')[0];
        document.getElementById('end-date').value = lastDay.toISOString().split('T')[0];
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-last-month').addEventListener('click', () => {
        const now = new Date();
        const firstDayLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastDayLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
        
        document.getElementById('start-date').value = firstDayLastMonth.toISOString().split('T')[0];
        document.getElementById('end-date').value = lastDayLastMonth.toISOString().split('T')[0];
        loadStats();
        loadAttendanceLogs();
    });
    
    document.getElementById('btn-filter').addEventListener('click', () => {
        loadStats();
        loadAttendanceLogs();
    });

    async function loadEmployeeData() {
        try {
            const response = await fetch(`/api/employees/${employeeId}?all=true`);
            const employee = await response.json();
            document.getElementById('employee-avatar').textContent = 
                (employee.first_name.charAt(0) + (employee.last_name.charAt(0) || '')).toUpperCase();
            document.getElementById('employee-name').textContent = employee.full_name;
            document.getElementById('employee-code').textContent = `كود الموظف: ${employee.employee_code}`;
            
            const detailsList = document.getElementById('employee-details');
            detailsList.innerHTML = `
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">الفرع</span>
                    <span class="fw-bold">${employee.branch_name || 'غير محدد'}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">القسم</span>
                    <span class="fw-bold">${employee.department_name || 'غير محدد'}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">الوظيفة</span>
                    <span class="fw-bold">${employee.job_title}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">تاريخ التوظيف</span>
                    <span class="fw-bold">${employee.hire_date}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">الهاتف</span>
                    <span class="fw-bold">${employee.phone || 'غير متاح'}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">التسجيل الوجه</span>
                    <span class="badge ${employee.face_enrolled ? 'bg-success' : 'bg-secondary'}">
                        ${employee.face_enrolled ? 'مسجل' : 'غير مسجل'}
                    </span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                    <span class="text-muted">الحالة</span>
                    <span class="badge ${employee.is_active ? 'bg-success' : 'bg-danger'}">
                        ${employee.is_active ? 'نشط' : 'غير نشط'}
                    </span>
                </li>
            `;
        } catch (err) {
            console.error(err);
        }
    }

    async function loadStats() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        try {
            let url = `/api/employees/${employeeId}/stats?all=true`;
            if (startDate) url += `&start_date=${startDate}`;
            if (endDate) url += `&end_date=${endDate}`;
            const response = await fetch(url);
            const stats = await response.json();
            
            document.getElementById('total-hours').textContent = `${stats.total_hours} ساعة`;
            document.getElementById('overtime-hours').textContent = `${stats.overtime_hours} ساعة`;
            document.getElementById('attendance-rate').textContent = `${stats.attendance_rate}%`;
            
            // Update charts
            updateWeeklyChart(stats);
            updatePieChart(stats);
        } catch (err) {
            console.error(err);
        }
    }

    async function loadAttendanceLogs() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        try {
            let url = `/api/employees/${employeeId}/attendance-logs?all=true`;
            if (startDate) url += `&start_date=${startDate}`;
            if (endDate) url += `&end_date=${endDate}`;
            const response = await fetch(url);
            const logs = await response.json();
            
            const tbody = document.getElementById('attendance-table-body');
            tbody.innerHTML = logs.map(log => `
                <tr>
                    <td>${log.check_time.split('T')[0]}</td>
                    <td>
                        <span class="badge ${getAttendanceTypeBadge(log.attendance_type)}">
                            ${getAttendanceTypeName(log.attendance_type)}
                        </span>
                    </td>
                    <td>${log.check_time.split('T')[1].substring(0, 8)}</td>
                    <td>${getVerifyTypeName(log.verify_type)}</td>
                    <td>${log.device_name || 'غير معروف'}</td>
                    <td>${log.branch_name || 'غير محدد'}</td>
                </tr>
            `).join('');
            
        } catch (err) {
            console.error(err);
        }
    }
    
    function getAttendanceTypeBadge(type) {
        const map = {
            'check_in': 'bg-primary',
            'check_out': 'bg-danger',
            'break_out': 'bg-warning',
            'break_in': 'bg-info',
            'ot_in': 'bg-success',
            'ot_out': 'bg-secondary',
        };
        return map[type] || 'bg-secondary';
    }
    
    function getAttendanceTypeName(type) {
        const map = {
            'check_in': 'حضور',
            'check_out': 'انصراف',
            'break_out': 'خروج استراحة',
            'break_in': 'عودة استراحة',
            'ot_in': 'بداية دوام إضافي',
            'ot_out': 'نهاية دوام إضافي',
        };
        return map[type] || type;
    }
    
    function getVerifyTypeName(type) {
        const map = {
            'fingerprint': 'بصمة',
            'card': 'بطاقة',
            'face': 'وجه',
            'password': 'كلمة مرور',
        };
        return map[type] || type;
    }
    
    function updateWeeklyChart(stats) {
        if (weeklyChart) weeklyChart.destroy();
        
        const ctx = document.getElementById('weekly-chart').getContext('2d');
        weeklyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة'],
                datasets: [
                    {
                        label: 'الحضور',
                        data: [stats.present_days, 0, 0, 0, 0, 0, 0],
                        backgroundColor: '#0d6efd',
                    },
                    {
                        label: 'التأخير',
                        data: [stats.late_days, 0, 0, 0, 0, 0, 0],
                        backgroundColor: '#ffc107',
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                },
            }
        });
    }
    
    function updatePieChart(stats) {
        if (pieChart) pieChart.destroy();
        
        const ctx = document.getElementById('attendance-pie-chart').getContext('2d');
        pieChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['الحضور', 'الغياب', 'التأخير'],
                datasets: [
                    {
                        data: [stats.present_days, stats.absent_days, stats.late_days],
                        backgroundColor: ['#198754', '#dc3545', '#ffc107'],
                    }
                ]
            },
            options: {
                responsive: true,
            }
        });
    }
});
