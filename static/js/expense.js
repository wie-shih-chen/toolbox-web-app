const expenseApp = {
    currentPeriod: { start: null, end: null },
    records: [],
    monthlyBudget: 10000,
    isTodayOnly: false,
    navStack: [],
    initialized: false,
    viewState: {
        level: 'weeks',
        currentWeek: null,
        currentDay: null
    },

    init() {
        if (this.initialized) return;
        this.initialized = true;
        const dashboard = document.querySelector('.expense-dashboard');
        if (dashboard) {
            this.currentPeriod.start = dashboard.dataset.startDate;
            this.currentPeriod.end = dashboard.dataset.endDate;
        }

        this.bindEvents();
        this.loadSettings().then(() => this.loadData());
    },

    initHistory() {
        this.bindEvents();
        this.initHistoryPriors();
    },

    initHistoryPriors() {
        // ... (previously established logic)
        const yearSelect = document.getElementById('yearSelect');
        const monthSelect = document.getElementById('monthSelect');
        if (!yearSelect) return;

        const now = new Date();
        const currentYear = now.getFullYear();
        yearSelect.innerHTML = '';
        for (let y = currentYear; y >= currentYear - 3; y--) {
            const opt = document.createElement('option');
            opt.value = y;
            opt.textContent = `${y} 年`;
            yearSelect.appendChild(opt);
        }

        let targetMonth = (now.getDate() < 10) ? now.getMonth() : now.getMonth() + 1;
        if (targetMonth === 0) { targetMonth = 12; yearSelect.value = currentYear - 1; }

        monthSelect.value = String(targetMonth).padStart(2, '0');
        this.updateDaysInMonth();
        this.loadHistoryData();

        yearSelect.addEventListener('change', () => { this.updateDaysInMonth(); this.loadHistoryData(); });
        monthSelect.addEventListener('change', () => { this.updateDaysInMonth(); this.loadHistoryData(); });
        const daySelect = document.getElementById('daySelect');
        if (daySelect) daySelect.addEventListener('change', () => this.loadHistoryData());

        const exportBtn = document.getElementById('exportCsvBtn');
        if (exportBtn) exportBtn.addEventListener('click', () => { this.triggerHaptic(); this.downloadCsv(); });
    },


    bindEvents() {
        const addSafeListener = (id, event, callback) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(event, callback);
        };

        addSafeListener('openAddExpenseBtn', 'click', () => this.openAddModal());
        addSafeListener('closeExpenseModalBtn', 'click', () => this.closeModal());
        addSafeListener('expenseForm', 'submit', (e) => this.handleSubmit(e));
        addSafeListener('deleteExpenseBtn', 'click', () => this.deleteCurrentRecord());

        addSafeListener('prevPeriodBtn', 'click', () => this.changePeriod(-1));
        addSafeListener('nextPeriodBtn', 'click', () => this.changePeriod(1));

        // Native Back Button
        addSafeListener('navBackButton', 'click', () => { this.triggerHaptic(); this.popNavigation(); });


        // Quick Tags Logic
        document.querySelectorAll('.tag-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const noteInput = document.getElementById('expenseNote');
                const categorySelect = document.getElementById('expenseCategory');
                if (noteInput) noteInput.value = pill.dataset.value;
                if (categorySelect) categorySelect.value = '飲食';
            });
        });



        window.onclick = (e) => { if (e.target.classList.contains('modal')) this.closeModal(); };
    },

    triggerHaptic() {
        if (navigator.vibrate) {
            navigator.vibrate(10); // Ultra light tap
        }
    },

    getActivePeriod() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();
        let start, end;

        if (now.getDate() >= 10) {
            start = new Date(year, month, 10);
            end = new Date(year, month + 1, 10);
        } else {
            start = new Date(year, month - 1, 10);
            end = new Date(year, month, 10);
        }
        return { start, end };
    },

    isDateEditable(dateStr) {
        const period = this.getActivePeriod();
        const date = new Date(dateStr);
        // Records on or after the start of current cycle are editable
        return date >= period.start;
    },


    async loadSettings() {
        try {
            const res = await fetch('/expense/api/settings');
            const data = await res.json();
            this.monthlyBudget = data.monthly_budget;
        } catch (error) { console.error(error); }
    },

    async loadData(preserveState = false) {
        if (this.isTodayOnly) return this.loadTodayData();
        if (!this.currentPeriod.start) return;

        const url = `/expense/api/records/grouped?start_date=${this.currentPeriod.start}&end_date=${this.currentPeriod.end}`;
        try {
            const res = await fetch(url);
            const data = await res.json();
            const display = document.getElementById('periodDisplayTitle');
            if (display) display.textContent = `${data.period.start} ~ ${data.period.end}`;

            const weekDisp = document.getElementById('weekDisplayRange');
            if (weekDisp && data.this_week_range) {
                weekDisp.textContent = `${data.this_week_range.start} ~ ${data.this_week_range.end}`;
            }
            this.groupedData = data;
            this.renderSummary(data.total_amount);

            if (!preserveState) {
                this.navStack = ['weeks'];
                this.switchLevel('weeks');
            } else {
                // Refresh the current level's DOM
                if (this.viewState.level === 'weeks') this.renderWeeks();
                else if (this.viewState.level === 'days') {
                    // Update currentWeek reference with new data from groupedData
                    const newWk = this.groupedData.weeks.find(w => w.week_start === this.viewState.currentWeek.week_start);
                    if (newWk) this.viewState.currentWeek = newWk;
                    this.renderDays(this.viewState.currentWeek);
                }
                else if (this.viewState.level === 'records') {
                    this.renderRecords(this.viewState.currentDay);
                }
            }
        } catch (error) { console.error(error); }
    },


    async loadTodayData() {
        const today = new Date();
        const offset = today.getTimezoneOffset() * 60000;
        const localDate = new Date(today - offset).toISOString().split('T')[0];
        const tomorrow = new Date(today.getTime() + 86400000 - offset).toISOString().split('T')[0];

        const res = await fetch(`/expense/api/records?start_date=${localDate}&end_date=${tomorrow}`);
        const data = await res.json();
        this.records = data.records;

        // Update today's total
        const total = data.total_amount || 0;
        const totalEl = document.getElementById('todayTotalAmount');
        if (totalEl) totalEl.textContent = `$${Math.round(total).toLocaleString()}`;

        this.renderList('expenseList');
    },


    // Navigation Logic (iOS Way)
    switchLevel(level, context = {}) {
        this.triggerHaptic();
        const container = document.getElementById('levelContainer');
        if (!container) return;

        container.className = `level-container level-${level}`;
        this.viewState.level = level;

        const localNav = document.getElementById('localNav');
        const levelTitle = document.getElementById('levelTitle');
        const backText = document.getElementById('backButtonText');

        if (level === 'weeks') {
            if (localNav) localNav.classList.add('hidden');
            this.renderWeeks();
        } else if (level === 'days') {
            if (localNav) localNav.classList.remove('hidden');
            if (backText) backText.textContent = '返回週期';
            if (levelTitle) levelTitle.textContent = `週份: ${context.week.week_start}`;
            this.viewState.currentWeek = context.week;
            this.renderDays(context.week);
        } else if (level === 'records') {
            if (localNav) localNav.classList.remove('hidden');
            if (backText) backText.textContent = '返回本週';
            if (levelTitle) levelTitle.textContent = `${context.day.date} 明細`;
            this.viewState.currentDay = context.day;
            this.renderRecords(context.day);
        }
    },


    popNavigation() {
        if (this.viewState.level === 'records') {
            this.switchLevel('days', { week: this.viewState.currentWeek });
        } else if (this.viewState.level === 'days') {
            this.switchLevel('weeks');
        }
    },

    renderWeeks() {
        const list = document.getElementById('weeklyList');
        if (!list) return;
        list.innerHTML = '';
        if (!this.groupedData.weeks.length) {
            list.innerHTML = '<p style="text-align:center; padding:20px; opacity:0.5;">本週期尚無花費</p>';
            return;
        }

        this.groupedData.weeks.forEach(wk => {
            const el = document.createElement('div');
            el.className = 'week-summary-card glass-premium';
            el.onclick = () => this.switchLevel('days', { week: wk });

            const startShort = wk.week_start.substring(5).replace('-', '/');
            const endShort = wk.week_end.substring(5).replace('-', '/');

            el.innerHTML = `
                <div class="card-info">
                    <span class="week-title">${startShort} ~ ${endShort}</span>
                    <span class="week-days-count">${wk.days.length} 天紀錄</span>
                </div>
                <div class="card-amount">$${Math.round(wk.total).toLocaleString()}</div>
                <span class="material-icons chevron">chevron_right</span>
            `;
            list.appendChild(el);
        });
    },

    renderDays(week) {
        const list = document.getElementById('dailyList');
        if (!list) return;
        list.innerHTML = '';
        week.days.forEach(day => {
            const el = document.createElement('div');
            el.className = 'day-summary-card glass-premium';
            el.onclick = () => this.switchLevel('records', { day: day });

            const dateObj = new Date(day.date);
            const weekDay = dateObj.toLocaleDateString('zh-TW', { weekday: 'short' });

            el.innerHTML = `
                <div class="card-info">
                    <span class="day-title">${day.date} (${weekDay})</span>
                    <span class="record-meta">${day.records_count} 筆消費</span>
                </div>
                <div class="card-amount">$${Math.round(day.total).toLocaleString()}</div>
                <span class="material-icons chevron">chevron_right</span>
            `;
            list.appendChild(el);
        });
    },

    async renderRecords(day) {
        const res = await fetch(`/expense/api/records?start_date=${day.date}&end_date=${new Date(new Date(day.date).getTime() + 86400000).toISOString().split('T')[0]}`);
        const data = await res.json();
        this.records = data.records;
        this.renderList('expenseList');
    },

    renderSummary(total) {
        const tel = document.getElementById('totalExpense');
        if (tel) tel.textContent = `$${Math.round(total).toLocaleString()}`;
        const rel = document.getElementById('remainingBudget');
        if (rel) rel.textContent = `$${Math.round(Math.max(0, this.monthlyBudget - total)).toLocaleString()}`;
        const pf = document.getElementById('budgetProgress');
        if (pf) pf.style.width = `${Math.min(100, (total / this.monthlyBudget) * 100)}%`;
    },

    renderList(cid) {
        const container = document.getElementById(cid);
        if (!container) return;
        container.innerHTML = '';
        if (this.records.length === 0) {
            container.innerHTML = '<p style="text-align:center; padding:30px; opacity:0.5;">無紀錄</p>';
            return;
        }
        const colorMap = {
            '飲食': 'var(--cat-food)',
            '飲料': 'var(--cat-food)',
            '衣著': 'var(--cat-clothing)',
            '居住': 'var(--cat-housing)',
            '交通': 'var(--cat-transport)',
            '教育': 'var(--cat-edu)',
            '娛樂': 'var(--cat-play)',
            '其他': 'var(--cat-other)'
        };

        const emojiMap = {
            '飲食': '🍽️',
            '衣著': '👕',
            '居住': '🏠',
            '交通': '🚌',
            '教育': '📖',
            '娛樂': '🎮',
            '其他': '📦'
        };

        this.records.forEach(r => {
            const item = document.createElement('div');
            item.className = 'expense-item';
            item.onclick = () => this.openEditModal(r);

            const categoryName = r.category ? (r.category.includes(' ') ? r.category.split(' ')[1] : r.category) : '其他';
            let catEmoji = r.category ? r.category.split(' ')[0] : (emojiMap[categoryName] || '📦');

            // Contextual emoji override for drinks within diet category
            if (categoryName === '飲食' && (r.note.includes('飲料') || r.note.includes('咖啡') || r.note.includes('茶'))) {
                catEmoji = '☕';
            }

            const catColor = colorMap[categoryName] || 'var(--cat-other)';

            item.innerHTML = `
                <div class="expense-item-left">
                    <div class="category-icon-wrapper" style="background: ${catColor}20; color: ${catColor}">${catEmoji}</div>
                    <div class="expense-details">
                        <span class="expense-name">${r.note}</span>
                        <div class="expense-meta"><span>${r.timestamp.substring(11, 16)} ${categoryName}</span></div>
                    </div>
                </div>
                <div class="expense-amount">$${Math.round(r.amount).toLocaleString()}</div>
            `;
            container.appendChild(item);
        });
    },

    openAddModal() {
        this.resetForm();
        const now = new Date();
        // Correctly handle local timezone offset for YYYY-MM-DD
        const offset = now.getTimezoneOffset() * 60000;
        const localISOTime = new Date(now - offset).toISOString();

        document.getElementById('expenseDate').value = localISOTime.split('T')[0];
        document.getElementById('expenseTime').value = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        document.getElementById('modalTitle').textContent = '新增支出';
        document.getElementById('deleteExpenseBtn').classList.add('hidden');

        const catSelect = document.getElementById('expenseCategory');
        if (catSelect) catSelect.disabled = false;

        // Reset read-only status for inputs
        document.querySelectorAll('#expenseForm input').forEach(input => {
            if (input.type !== 'hidden') {
                input.readOnly = false;
                input.disabled = false;
            }
        });
        const submitBtn = document.querySelector('#expenseForm button[type="submit"]');
        if (submitBtn) submitBtn.classList.remove('hidden');

        this.triggerHaptic();
        document.getElementById('expenseModal').classList.add('show');
    },

    openEditModal(record) {
        this.resetForm();
        const isEditable = this.isDateEditable(record.timestamp.split(' ')[0]);

        document.getElementById('expenseId').value = record.id;
        document.getElementById('expenseNote').value = record.note;
        document.getElementById('expenseAmount').value = record.amount;
        document.getElementById('expenseDate').value = record.timestamp.split(' ')[0];
        document.getElementById('expenseTime').value = record.timestamp.split(' ')[1].substring(0, 5);

        document.getElementById('modalTitle').textContent = isEditable ? '編輯支出' : '查看支出 (唯讀)';

        if (record.category) {
            const catName = record.category.includes(' ') ? record.category.split(' ')[1] : record.category;
            document.getElementById('expenseCategory').value = catName;
        }

        // Lock category on edit or if read-only
        const catSelect = document.getElementById('expenseCategory');
        if (catSelect) catSelect.disabled = true;

        // Force read-only state for past periods
        document.querySelectorAll('#expenseForm input').forEach(input => {
            if (input.type !== 'hidden') input.readOnly = !isEditable;
        });

        const deleteBtn = document.getElementById('deleteExpenseBtn');
        const submitBtn = document.querySelector('#recordForm button[type="submit"]');
        const quickTags = document.getElementById('mealQuickTags');

        if (deleteBtn) deleteBtn.classList.toggle('hidden', !isEditable);
        if (submitBtn) submitBtn.classList.toggle('hidden', !isEditable);
        if (quickTags) quickTags.classList.toggle('hidden', !isEditable);

        this.triggerHaptic();
        document.getElementById('expenseModal').classList.add('show');
    },



    closeModal() { document.getElementById('expenseModal').classList.remove('show'); },
    resetForm() {
        document.getElementById('expenseForm').reset();
        const id = document.getElementById('expenseId');
        if (id) id.value = '';
    },

    async handleSubmit(e) {
        e.preventDefault();
        const fd = new FormData(e.target);
        const data = Object.fromEntries(fd.entries());
        data.timestamp = `${document.getElementById('expenseDate').value} ${document.getElementById('expenseTime').value}:00`;
        const id = data.id;
        const res = await fetch(id ? `/expense/api/records/${id}` : '/expense/api/records', {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            this.triggerHaptic();
            this.closeModal();
            this.loadData(true); // Preserve state!
        }
    },



    async deleteCurrentRecord() {
        if (!confirm('刪除？')) return;
        this.triggerHaptic();
        const id = document.getElementById('expenseId').value;
        const res = await fetch(`/expense/api/records/${id}`, { method: 'DELETE' });
        if (res.ok) {
            this.closeModal();
            this.loadData(true); // Preserve state!
        }
    },



    changePeriod(delta) {
        const d = new Date(this.currentPeriod.start);
        d.setMonth(d.getMonth() + delta);
        this.currentPeriod.start = this.formatDate(d);
        const n = new Date(d); n.setMonth(n.getMonth() + 1);
        this.currentPeriod.end = this.formatDate(n);
        this.loadData();
    },
    formatDate(d) { return d.toISOString().split('T')[0]; },
    updateDaysInMonth() {
        const y = parseInt(document.getElementById('yearSelect').value);
        const m = parseInt(document.getElementById('monthSelect').value);
        const ds = document.getElementById('daySelect');
        if (!ds) return;
        const dim = new Date(y, m, 0).getDate();
        ds.innerHTML = '<option value="">全月份</option>';
        for (let i = 1; i <= dim; i++) {
            const opt = document.createElement('option');
            opt.value = String(i).padStart(2, '0');
            opt.textContent = `${i} 號`;
            ds.appendChild(opt);
        }
    },
    async loadHistoryData() {
        const y = document.getElementById('yearSelect').value;
        const m = document.getElementById('monthSelect').value;
        const d = document.getElementById('daySelect').value;
        const s = d ? `${y}-${m}-${d}` : `${y}-${m}-10`;
        let e;
        if (d) {
            e = new Date(new Date(s).getTime() + 86400000).toISOString().split('T')[0];
        } else {
            let ey = parseInt(y); let em = parseInt(m) + 1; if (em > 12) { em = 1; ey++; }
            e = `${ey}-${String(em).padStart(2, '0')}-10`;
        }
        const res = await fetch(`/expense/api/records?start_date=${s}&end_date=${e}`);
        const data = await res.json();
        this.records = data.records;
        const ht = document.getElementById('historyTotal'); if (ht) ht.textContent = `$${Math.round(data.total_amount).toLocaleString()}`;
        this.renderList('historyExpenseList');
    },
    downloadCsv() {
        // Simplified range logic for download
        const y = document.getElementById('yearSelect').value;
        const m = document.getElementById('monthSelect').value;
        const d = document.getElementById('daySelect').value;
        const s = d ? `${y}-${m}-${d}` : `${y}-${m}-10`;
        let e;
        if (d) { e = new Date(new Date(s).getTime() + 86400000).toISOString().split('T')[0]; }
        else { let ey = parseInt(y); let em = parseInt(m) + 1; if (em > 12) { em = 1; ey++; } e = `${ey}-${String(em).padStart(2, '0')}-10`; }
        window.location.href = `/expense/api/records/export?start_date=${s}&end_date=${e}`;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.expense-dashboard')) {
        if (document.querySelector('.today-view')) {
            expenseApp.isTodayOnly = true;
        }
        expenseApp.init();
    }
    else if (document.querySelector('.expense-history')) expenseApp.initHistory();
    else if (document.querySelector('.expense-settings')) expenseApp.initSettings();
});

