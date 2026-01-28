const salaryApp = {
    currentWeekStart: null,
    records: [],

    init() {
        const startDateStr = document.querySelector('.salary-dashboard').dataset.startDate;
        this.currentWeekStart = new Date(startDateStr);

        this.bindEvents();
        this.loadWeek();
    },

    bindEvents() {
        const addSafeListener = (id, event, callback) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(event, callback);
        };

        addSafeListener('prevWeekBtn', 'click', () => this.changeWeek(-7));
        addSafeListener('nextWeekBtn', 'click', () => this.changeWeek(7));
        addSafeListener('todayBtn', 'click', () => this.goToToday());

        addSafeListener('prevMonthBtn', 'click', () => this.changeMonth(-1));
        addSafeListener('nextMonthBtn', 'click', () => this.changeMonth(1));
        addSafeListener('thisMonthBtn', 'click', () => {
            const n = new Date();
            this.currentMonth = new Date(n.getFullYear(), n.getMonth(), 1);
            this.loadMonth();
        });

        // Actions
        addSafeListener('copyLastWeekBtn', 'click', () => this.copyLastWeek());
        addSafeListener('clearThisWeekBtn', 'click', () => this.clearThisWeek());

        // Modal Events
        const closeBtns = document.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => this.closeModal()));

        addSafeListener('recordForm', 'submit', (e) => this.handleSubmit(e));
        addSafeListener('deleteBtn', 'click', () => this.deleteCurrentRecord());

        // Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Close modal on outside click
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) this.closeModal();
        });
    },

    async loadWeek() {
        const startStr = this.formatDate(this.currentWeekStart);
        const end = new Date(this.currentWeekStart);
        end.setDate(end.getDate() + 6);
        const endStr = this.formatDate(end);

        // Update Label
        document.getElementById('currentWeekLabel').textContent =
            `${startStr.replace(/-/g, '/')} - ${endStr.slice(5).replace(/-/g, '/')}`;

        // Fetch Data
        try {
            const response = await fetch(`/salary/api/records?start_date=${startStr}&end_date=${endStr}`);
            this.records = await response.json();
            this.renderGrid();
            this.updateSummary();
        } catch (error) {
            console.error('Error loading data:', error);
            alert('無法載入資料');
        }
    },

    renderGrid() {
        // Clear all columns
        document.querySelectorAll('.shifts-container').forEach(el => el.innerHTML = '');

        // Reset Date Headers
        const days = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
        const todayStr = this.formatDate(new Date());

        for (let i = 0; i < 7; i++) {
            const currentDay = new Date(this.currentWeekStart);
            currentDay.setDate(this.currentWeekStart.getDate() + i);
            const dateStr = this.formatDate(currentDay);

            const col = document.querySelector(`.day-column[data-day-index="${i}"]`);
            col.querySelector('.day-date').textContent = `${currentDay.getMonth() + 1}/${currentDay.getDate()}`;

            // Highlight today
            if (dateStr === todayStr) {
                col.classList.add('today');
            } else {
                col.classList.remove('today');
            }

            // Find records for this day
            const dayRecords = this.records.filter(r => r.date === dateStr);
            const container = col.querySelector('.shifts-container');

            dayRecords.forEach(record => {
                const card = document.createElement('div');
                card.className = `shift-card ${record.type === 'bonus' ? 'bonus' : ''}`;
                card.onclick = () => this.openEditModal(record);

                if (record.type === 'shift') {
                    card.innerHTML = `
                        <div class="shift-time">${record.start_time} - ${record.end_time}</div>
                        <div class="shift-info">
                            <span>${record.hours}h</span>
                            <span>$${Math.round(record.amount)}</span>
                        </div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="shift-time" style="color:#ffd700">💰 獎金 $${record.amount}</div>
                        <div class="shift-info">
                            <span>${record.note || ''}</span>
                        </div>
                    `;
                }
                container.appendChild(card);
            });
        }
    },

    updateSummary() {
        let hours = 0;
        let amount = 0;

        this.records.forEach(r => {
            if (r.type === 'shift') hours += r.hours;
            amount += r.amount;
        });

        document.getElementById('weeklyHours').textContent = `${hours.toFixed(1)}h`;
        document.getElementById('weeklyAmount').textContent = `$${Math.round(amount)}`;
    },

    changeWeek(days) {
        this.currentWeekStart.setDate(this.currentWeekStart.getDate() + days);
        this.loadWeek();
    },

    goToToday() {
        const now = new Date();
        const day = now.getDay() || 7; // Sunday is 0 -> 7
        now.setDate(now.getDate() - day + 1); // Go to Monday
        this.currentWeekStart = now;
        this.loadWeek();
    },

    // Modal Handling
    openAddModal(dayIndex) {
        const targetDate = new Date(this.currentWeekStart);
        targetDate.setDate(targetDate.getDate() + dayIndex);

        this.resetForm();
        document.getElementById('recordDate').value = this.formatDate(targetDate);
        document.getElementById('modalTitle').textContent = `新增紀錄 (${targetDate.getMonth() + 1}/${targetDate.getDate()})`;
        document.getElementById('deleteBtn').classList.add('hidden');
        this.switchTab('shift');

        document.getElementById('recordModal').classList.add('show');
    },

    openEditModal(record) {
        this.resetForm();
        document.getElementById('recordId').value = record.id;
        document.getElementById('recordDate').value = record.date;
        document.getElementById('recordType').value = record.type;
        document.getElementById('modalTitle').textContent = '編輯紀錄';
        document.getElementById('deleteBtn').classList.remove('hidden');

        if (record.type === 'shift') {
            this.switchTab('shift');
            document.getElementById('startTime').value = record.start_time;
            document.getElementById('endTime').value = record.end_time;
            document.getElementById('shiftRate').value = record.rate || '';
        } else {
            this.switchTab('bonus');
            document.getElementById('bonusAmount').value = record.amount;
            document.getElementById('bonusNote').value = record.note;
        }

        document.getElementById('recordModal').classList.add('show');
    },

    closeModal() {
        document.getElementById('recordModal').classList.remove('show');
    },

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
        document.getElementById('recordType').value = tabName;
    },

    resetForm() {
        document.getElementById('recordForm').reset();
        document.getElementById('recordId').value = '';
        // Set defaults
        document.getElementById('startTime').value = '09:00';
        document.getElementById('endTime').value = '18:00';
        const rateInput = document.getElementById('shiftRate');
        if (rateInput) rateInput.value = '';
    },

    // API Actions
    async handleSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        const id = data.id;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/salary/api/records/${id}` : '/salary/api/records';

        // Manual Validation/Calc for frontend specific logic if needed
        // but backend logic handles hours calc
        if (data.type === 'shift') {
            // Check start < end?
            // Simple check
            if (data.start_time >= data.end_time) {
                alert('結束時間必須晚於開始時間');
                return;
            }
            data.hours = this.calculateHours(data.start_time, data.end_time);
        }

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                this.closeModal();
                // Page-aware refresh
                if (document.querySelector('.salary-dashboard')) {
                    this.loadWeek();
                } else if (document.querySelector('.salary-monthly')) {
                    this.loadMonth();
                } else if (document.querySelector('.salary-history')) {
                    this.loadHistoryData();
                }
            } else {
                const err = await res.json();
                alert(err.error || '儲存失敗');
            }
        } catch (error) {
            console.error(error);
            alert('網路錯誤');
        }
    },

    async deleteCurrentRecord() {
        if (!confirm('確定要刪除嗎？')) return;

        const id = document.getElementById('recordId').value;
        if (!id) return;

        try {
            const res = await fetch(`/salary/api/records/${id}`, { method: 'DELETE' });
            if (res.ok) {
                this.closeModal();
                this.loadWeek();
            } else {
                alert('刪除失敗');
            }
        } catch (error) {
            console.error(error);
        }
    },

    async copyLastWeek() {
        if (!confirm('確定要複製上週的班表到本週嗎？\n(注意：如果本週已有排班，將會重複新增)')) return;

        const targetDate = this.formatDate(this.currentWeekStart);

        try {
            const res = await fetch('/salary/api/actions/copy_week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_date: targetDate })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.count === 0) {
                    alert('上週沒有排班紀錄');
                } else {
                    alert(`已複製 ${data.count} 筆紀錄`);
                    this.loadWeek();
                }
            } else {
                alert('複製失敗');
            }
        } catch (error) {
            console.error(error);
            alert('網路錯誤');
        }
    },

    async clearThisWeek() {
        if (!confirm('確定要清空本週的所有排班與獎金嗎？\n此操作無法復原！')) return;

        const weekStart = this.formatDate(this.currentWeekStart);

        try {
            const res = await fetch('/salary/api/actions/clear_week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week_start: weekStart })
            });

            if (res.ok) {
                const data = await res.json();
                alert(`已刪除 ${data.count} 筆紀錄`);
                this.loadWeek();
            } else {
                alert('刪除失敗');
            }
        } catch (error) {
            console.error(error);
        }
    },

    // Utils
    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

    calculateHours(start, end) {
        const [h1, m1] = start.split(':').map(Number);
        const [h2, m2] = end.split(':').map(Number);
        const d1 = new Date(0, 0, 0, h1, m1);
        const d2 = new Date(0, 0, 0, h2, m2);
        return (d2 - d1) / 36e5;
    },

    // Monthly View Logic
    initMonthly() {
        const now = new Date();
        this.currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);

        this.bindEvents();
        this.loadMonth();
    },

    changeMonth(delta) {
        this.currentMonth.setMonth(this.currentMonth.getMonth() + delta);
        this.loadMonth();
    },

    async loadMonth() {
        const y = this.currentMonth.getFullYear();
        const m = this.currentMonth.getMonth();

        document.getElementById('currentMonthLabel').textContent = `${y}年 ${String(m + 1).padStart(2, '0')}月`;

        // 1. Calculate Grid Range (Visual Calendar)
        const firstDayOfMonth = new Date(y, m, 1);
        const lastDayOfMonth = new Date(y, m + 1, 0);

        const startDay = firstDayOfMonth.getDay() || 7; // 1 (Mon) - 7 (Sun)
        const gridStart = new Date(firstDayOfMonth);
        gridStart.setDate(1 - (startDay - 1));

        const gridEnd = new Date(gridStart);
        gridEnd.setDate(gridStart.getDate() + 41);

        // 2. Calculate Pay Period Range (For Summary)
        // User rule: This Month 10th to Next Month 10th
        const payStart = new Date(y, m, 10);
        const payEnd = new Date(y, m + 1, 10);

        // 3. Determine Fetch Range (Union of both)
        // We need to ensure we fetch enough data for both the grid and the summary
        const fetchStart = gridStart < payStart ? gridStart : payStart;
        const fetchEnd = gridEnd > payEnd ? gridEnd : payEnd;

        try {
            const response = await fetch(`/salary/api/records?start_date=${this.formatDate(fetchStart)}&end_date=${this.formatDate(fetchEnd)}`);
            this.records = await response.json();

            this.renderCalendar(gridStart);
            // Pass pay period instead of calendar month
            this.updateMonthlySummary(payStart, payEnd);
        } catch (error) {
            console.error(error);
        }
    },

    renderCalendar(startDate) {
        const container = document.getElementById('calendarBody');
        container.innerHTML = '';
        const todayStr = this.formatDate(new Date());

        for (let i = 0; i < 42; i++) {
            const current = new Date(startDate);
            current.setDate(startDate.getDate() + i);
            const dateStr = this.formatDate(current);
            const isOtherMonth = current.getMonth() !== this.currentMonth.getMonth();

            const cell = document.createElement('div');
            cell.className = `calendar-day ${isOtherMonth ? 'other-month' : ''} ${dateStr === todayStr ? 'today' : ''}`;

            // Header
            const header = document.createElement('div');
            header.className = 'cal-day-header';
            header.textContent = current.getDate();
            cell.appendChild(header);

            // Content
            const content = document.createElement('div');
            content.className = 'cal-day-content';

            // We need a closure for onclick to capture current date correctly
            // But 'current' is block scoped in let, so it should be fine.
            // However, to reuse logic, let's just use openAddModalForDate
            cell.onclick = () => this.openAddModalForDate(new Date(current)); // pass copy

            // Find records
            const dayRecords = this.records.filter(r => r.date === dateStr);
            dayRecords.forEach(r => {
                const item = document.createElement('div');
                item.className = 'cal-item';
                if (r.type === 'shift') {
                    item.textContent = `• ${r.start_time}`;
                } else {
                    item.textContent = `• 💰`;
                    item.style.color = '#ffd700';
                }
                item.onclick = (e) => {
                    e.stopPropagation();
                    this.openEditModal(r);
                };
                content.appendChild(item);
            });

            cell.appendChild(content);
            container.appendChild(cell);
        }
    },

    openAddModalForDate(date) {
        this.currentWeekStart = date;
        this.resetForm();
        document.getElementById('recordDate').value = this.formatDate(date);
        document.getElementById('modalTitle').textContent = `新增紀錄 (${date.getMonth() + 1}/${date.getDate()})`;
        document.getElementById('deleteBtn').classList.add('hidden');
        this.switchTab('shift');
        document.getElementById('recordModal').classList.add('show');
    },

    updateMonthlySummary(start, end) {
        const startStr = this.formatDate(start);
        const endStr = this.formatDate(end);

        let hours = 0;
        let amount = 0;

        this.records.forEach(r => {
            if (r.date >= startStr && r.date <= endStr) {
                if (r.type === 'shift') hours += r.hours;
                amount += r.amount;
            }
        });

        document.getElementById('monthlyHours').textContent = `${hours.toFixed(1)}h`;
        document.getElementById('monthlyAmount').textContent = `$${Math.round(amount)}`;
    },

    // History Logic
    initHistory() {
        this.bindEvents();
        const select = document.getElementById('periodSelect');
        if (select) select.addEventListener('change', () => this.loadHistoryData());

        // Load Periods
        this.loadHistoryPeriods();
    },

    async loadHistoryPeriods() {
        try {
            const res = await fetch('/salary/api/history/periods');
            const periods = await res.json();

            const select = document.getElementById('periodSelect');
            select.innerHTML = '';

            if (periods.length === 0) {
                const opt = document.createElement('option');
                opt.textContent = '無資料';
                select.appendChild(opt);
                return;
            }

            let defaultSelected = null;
            const today = new Date();
            const todayStr = this.formatDate(today);
            console.log("Checking history for today:", todayStr);

            periods.forEach(p => {
                const opt = document.createElement('option');
                opt.value = `${p.start},${p.end}`;
                opt.textContent = p.label;
                select.appendChild(opt);

                // Compare strings YYYY-MM-DD
                if (todayStr >= p.start && todayStr <= p.end) {
                    console.log(`Match found: ${p.label}`);
                    defaultSelected = opt.value;
                }
            });

            // Auto-select current month if found
            if (defaultSelected) {
                select.value = defaultSelected;
            } else {
                console.log("No match found, selecting last item");
                // Default to the last one (newest if asc) or just the last one available
                if (select.options.length > 0) {
                    select.selectedIndex = select.options.length - 1;
                }
            }

            // Trigger load data
            this.loadHistoryData();
        } catch (error) {
            console.error(error);
        }
    },

    async loadHistoryData() {
        const select = document.getElementById('periodSelect');
        if (!select.value) return;

        const [start, end] = select.value.split(',');

        try {
            const res = await fetch(`/salary/api/history/data?start_date=${start}&end_date=${end}`);
            const data = await res.json();

            // Update Summary
            document.getElementById('historyHours').textContent = `${data.total_hours.toFixed(1)}h`;
            document.getElementById('historyAmount').textContent = `$${Math.round(data.total_amount)}`;
            document.getElementById('historyCount').textContent = data.record_count;

            // Update Table
            const tbody = document.getElementById('historyTableBody');
            tbody.innerHTML = '';

            // Sort records by date descending for list view
            data.records.sort((a, b) => a.date < b.date ? 1 : -1);

            data.records.forEach(r => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.onclick = () => this.openEditModal(r);

                if (r.type === 'shift') {
                    tr.innerHTML = `
                        <td>${r.date}</td>
                        <td>排班</td>
                        <td>${r.start_time} - ${r.end_time}</td>
                        <td>${r.hours}</td>
                        <td>${r.rate}/hr -> $${Math.round(r.amount)}</td>
                        <td></td>
                    `;
                } else {
                    tr.innerHTML = `
                        <td>${r.date}</td>
                        <td style="color:#ffd700">獎金</td>
                        <td></td>
                        <td></td>
                        <td>$${r.amount}</td>
                        <td>${r.note || ''}</td>
                    `;
                }
                tbody.appendChild(tr);
            });

        } catch (error) {
            console.error(error);
        }
    },

    // Settings Logic
    initSettings() {
        document.getElementById('settingsForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/salary/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (res.ok) {
                    alert('設定已儲存');
                } else {
                    alert('儲存失敗');
                }
            } catch (error) {
                console.error(error);
                alert('網路錯誤');
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Detect Page
    if (document.querySelector('.salary-dashboard')) {
        salaryApp.init();
    } else if (document.querySelector('.salary-monthly')) {
        salaryApp.initMonthly();
    } else if (document.querySelector('.salary-history')) {
        salaryApp.initHistory();
    } else if (document.querySelector('.settings-container')) {
        salaryApp.initSettings();
    }
});
