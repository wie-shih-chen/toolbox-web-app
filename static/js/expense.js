const expenseApp = {
    currentPeriod: { start: null, end: null },
    records: [],
    settings: {}, // Store full settings object
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
            // Check if this is the today-only view
            if (dashboard.dataset.todayOnly === 'true') {
                this.isTodayOnly = true;
            }
        }

        this.bindEvents();
        this.loadSettings().then(() => {
            // If cycle day is set, override the period from HTML (which might be default month)
            if (this.settings.billing_cycle_start_day && this.settings.billing_cycle_start_day !== 1) {
                // Determine current cycle based on Today
                const cycle = this.getCycleDates(new Date());
                // Wait, if viewing history? Dashboard usually defaults to 'Active' cycle (Now).
                // If user wants to see specific past month, they nav.
                this.currentPeriod = cycle;
            }
            this.loadData();
        });
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

        // Default to current month
        let targetMonth = now.getMonth() + 1;

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
        const range = this.settings.editable_month_range !== undefined ? this.settings.editable_month_range : 1;
        if (range === -1) return { start: new Date(2000, 0, 1) };

        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth() - range, 1);
        return { start };
    },


    isDateEditable(dateStr) {
        const period = this.getActivePeriod();
        const date = new Date(dateStr);
        // Records on or after the start of current cycle are editable
        return date >= period.start;
    },


    async loadSettings() {
        try {
            const res = await fetch(`/expense/api/settings?t=${new Date().getTime()}`);
            this.settings = await res.json();
            console.log("DATA_CHECK: Server returned:", this.settings);
            this.monthlyBudget = this.settings.monthly_budget || 10000;

            // Parse JSON strings
            // Parse JSON strings and FILTER NULLs
            try {
                const rawCats = JSON.parse(this.settings.custom_categories || '[]');
                this.settings.custom_categories = Array.isArray(rawCats) ? rawCats.filter(c => c && typeof c === 'object') : [];
            } catch (e) {
                console.error("JSON PARSE FAIL (Categories):", e);
                this.settings.custom_categories = [];
            }
            try {
                const rawRecs = JSON.parse(this.settings.recurring_expenses || '[]');
                this.settings.recurring_expenses = Array.isArray(rawRecs) ? rawRecs.filter(r => r && typeof r === 'object') : [];
            } catch (e) {
                console.error("JSON PARSE FAIL (Recurring):", e);
                this.settings.recurring_expenses = [];
            }
            try {
                const rawShorts = JSON.parse(this.settings.quick_shortcuts || '[]');
                let parsedShorts = [];

                if (Array.isArray(rawShorts)) {
                    parsedShorts = rawShorts.map(s => {
                        // Migration: Convert old string format to object
                        if (typeof s === 'string') return { name: s, emoji: '⚡' }; // Default emoji for migrated items
                        if (typeof s === 'object' && s.name) return s;
                        return null;
                    }).filter(s => s);
                }

                // If DB has no shortcuts, use defaults with Emojis
                if (parsedShorts.length === 0) {
                    this.settings.quick_shortcuts = [
                        { name: '早餐', emoji: '🍳' },
                        { name: '午餐', emoji: '🍱' },
                        { name: '晚餐', emoji: '🍜' },
                        { name: '宵夜', emoji: '🍢' },
                        { name: '飲料', emoji: '🥤' }
                    ];
                } else {
                    this.settings.quick_shortcuts = parsedShorts;
                }
            } catch (e) {
                console.error("JSON PARSE FAIL (Shortcuts):", e);
                this.settings.quick_shortcuts = [
                    { name: '早餐', emoji: '🍳' },
                    { name: '午餐', emoji: '🍱' },
                    { name: '晚餐', emoji: '🍜' },
                    { name: '宵夜', emoji: '🍢' },
                    { name: '飲料', emoji: '🥤' }
                ];
            }



            // Initialize defaults if empty (First run)
            if (this.settings.custom_categories.length === 0) {
                this.settings.custom_categories = [
                    { name: '飲食', emoji: '🍽️', color: 'var(--cat-food)' },
                    { name: '衣著', emoji: '👕', color: 'var(--cat-clothing)' },
                    { name: '居住', emoji: '🏠', color: 'var(--cat-housing)' },
                    { name: '交通', emoji: '🚌', color: 'var(--cat-transport)' },
                    { name: '教育', emoji: '📖', color: 'var(--cat-edu)' },
                    { name: '娛樂', emoji: '🎮', color: 'var(--cat-play)' },
                    { name: '其他', emoji: '📦', color: 'var(--cat-other)' }
                ];
            }

            this.populateCategorySelect();

        } catch (error) { console.error(error); }
    },

    populateCategorySelect() {
        const select = document.getElementById('expenseCategory');
        if (!select) return;

        select.innerHTML = '';

        // Use ONLY managed categories (which now include defaults)
        if (this.settings.custom_categories && Array.isArray(this.settings.custom_categories)) {
            this.settings.custom_categories.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.name;
                opt.textContent = `${c.emoji || '🏷️'} ${c.name}`;
                select.appendChild(opt);
            });
        }
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
        const localDate = this.formatDate(today);
        const tomorrow = this.formatDate(new Date(today.getTime() + 86400000));


        const res = await fetch(`/expense/api/records?start_date=${localDate}&end_date=${tomorrow}`);
        const data = await res.json();
        this.records = data.records;

        // Update today's total
        const total = data.total_amount || 0;
        const totalEl = document.getElementById('todayTotalAmount');
        if (totalEl) totalEl.textContent = `$${Math.round(total).toLocaleString()}`;

        this.renderList('expenseList');
        this.updateMonthlyStatus();
    },

    getCycleDates(refDate = new Date()) {
        const cycleDay = this.settings.billing_cycle_start_day || 10;
        const currentDay = refDate.getDate();

        let startYear = refDate.getFullYear();
        let startMonth = refDate.getMonth();

        // If today is before cycle day, the cycle started last month
        if (currentDay < cycleDay) {
            startMonth--;
        }

        const start = new Date(startYear, startMonth, cycleDay);
        const end = new Date(startYear, startMonth + 1, cycleDay); // End date exclusive usually, or handles "day before"
        // API expects inclusive date strings usually, but let's check backend.
        // For date string "YYYY-MM-DD", let's use [Start, End - 1 day]

        const endInclusive = new Date(startYear, startMonth + 1, cycleDay - 1);

        return {
            start: this.formatDate(start),
            end: this.formatDate(endInclusive)
        };
    },

    async updateMonthlyStatus() {
        // Ensure settings are loaded
        if (!this.settings.billing_cycle_start_day) await this.loadSettings();

        const cycle = this.getCycleDates();
        const start = cycle.start;
        const end = cycle.end;

        try {
            const res = await fetch(`/expense/api/records?start_date=${start}&end_date=${end}`);
            const data = await res.json();
            // Calculate total for the whole month
            const total = data.records.reduce((sum, r) => sum + r.amount, 0);

            // Re-use renderSummary to update remaining budget & progress bar
            this.renderSummary(total);
        } catch (e) { console.error('Error fetching monthly status:', e); }
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
        const nextDay = new Date(new Date(day.date).getTime() + 86400000);
        const res = await fetch(`/expense/api/records?start_date=${day.date}&end_date=${this.formatDate(nextDay)}`);

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

        if (pf) {
            const percent = (total / this.monthlyBudget) * 100;
            pf.style.width = `${Math.min(100, percent)}%`;

            // Alert Threshold Logic
            const threshold = this.settings.budget_alert_threshold || 80;
            if (percent >= 100) {
                pf.style.background = '#ef4444'; // Red for over budget
            } else if (percent >= threshold) {
                pf.style.background = '#f59e0b'; // Amber/Orange for warning
            } else {
                pf.style.background = 'var(--accent-color)'; // Default
            }
        }
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

        // Merge custom categories
        if (this.settings.custom_categories) {
            this.settings.custom_categories.forEach(c => {
                colorMap[c.name] = c.color;
                emojiMap[c.name] = c.emoji;
            });
        }

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

        document.getElementById('expenseDate').value = this.formatDate(now);
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

        // Dynamic Shortcuts
        const tagsContainer = document.getElementById('mealQuickTags');
        if (tagsContainer) {
            tagsContainer.innerHTML = '';

            // Check if shortcuts exist, otherwise use defaults
            let shortcuts = this.settings.quick_shortcuts;
            if (!shortcuts || shortcuts.length === 0) {
                shortcuts = [
                    { name: '早餐', emoji: '🍳' },
                    { name: '午餐', emoji: '🍱' },
                    { name: '晚餐', emoji: '🍜' },
                    { name: '宵夜', emoji: '🍢' },
                    { name: '飲料', emoji: '🥤' }
                ];
            }

            shortcuts.forEach(item => {
                // Ensure item is object (backward compatibility safecheck)
                const name = typeof item === 'string' ? item : item.name;
                const emoji = typeof item === 'string' ? '' : (item.emoji || '');

                const pill = document.createElement('div');
                pill.className = 'tag-pill';
                pill.textContent = `${emoji} ${name}`;
                pill.dataset.value = name;

                pill.onclick = () => {
                    document.getElementById('expenseNote').value = name;

                    // specific logic for drink/food if needed
                    if (name.includes('飲料') || name.includes('茶') || name.includes('咖啡')) {
                        document.getElementById('expenseCategory').value = '飲食';
                    }
                };
                tagsContainer.appendChild(pill);
            });
        }

        // Enforce cycle boundary for adding records
        const period = this.getActivePeriod();
        const dateInput = document.getElementById('expenseDate');
        if (dateInput) {
            dateInput.min = this.formatDate(period.start);
        }

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
        const formElements = document.querySelectorAll('#expenseForm input, #expenseForm select, #expenseForm textarea');
        formElements.forEach(el => {
            if (el.type !== 'hidden') {
                el.readOnly = !isEditable;
                el.disabled = !isEditable;
            }
        });

        const deleteBtn = document.getElementById('deleteExpenseBtn');
        const submitBtn = document.querySelector('#expenseForm button[type="submit"]');
        const quickTags = document.getElementById('mealQuickTags');

        if (deleteBtn) deleteBtn.classList.toggle('hidden', !isEditable);
        if (submitBtn) submitBtn.classList.toggle('hidden', !isEditable);
        if (quickTags) quickTags.classList.toggle('hidden', !isEditable);

        this.triggerHaptic();
        document.getElementById('expenseModal').classList.add('show');
    },

    refreshData() {
        if (document.querySelector('.today-view')) {
            this.loadTodayData();
        } else if (document.querySelector('.expense-dashboard')) {
            this.loadData(true);
        } else if (document.querySelector('.expense-history')) {
            this.loadHistoryData();
        }
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
            this.refreshData();
        }

    },



    async deleteCurrentRecord() {
        if (!confirm('刪除？')) return;
        this.triggerHaptic();
        const id = document.getElementById('expenseId').value;
        const res = await fetch(`/expense/api/records/${id}`, { method: 'DELETE' });
        if (res.ok) {
            this.closeModal();
            this.refreshData();
        }

    },



    changePeriod(delta) {
        const cycleDay = this.settings.billing_cycle_start_day || 1;
        // Parse current start to get Y, M
        const currentStart = new Date(this.currentPeriod.start);
        let y = currentStart.getFullYear();
        let m = currentStart.getMonth();

        // Move month
        m += delta;

        const start = new Date(y, m, cycleDay);
        // End is next month cycle day - 1 day (inclusive end for API)
        const end = new Date(start.getFullYear(), start.getMonth() + 1, cycleDay - 1);

        this.currentPeriod = {
            start: this.formatDate(start),
            end: this.formatDate(end)
        };
        this.loadData();
    },
    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

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
        const s = d ? `${y}-${m}-${d}` : `${y}-${m}-01`;
        let e;
        if (d) {
            e = this.formatDate(new Date(new Date(s).getTime() + 86400000));
        } else {
            let dim = new Date(y, m, 0).getDate();
            e = `${y}-${m}-${dim}`;
        }
        const res = await fetch(`/expense/api/records?start_date=${s}&end_date=${e}`);
        const data = await res.json();
        this.records = data.records;
        const ht = document.getElementById('historyTotal'); if (ht) ht.textContent = `$${Math.round(data.total_amount).toLocaleString()}`;
        this.renderList('historyExpenseList');
    },
    async downloadCsv() {
        const y = document.getElementById('yearSelect').value;
        const m = document.getElementById('monthSelect').value;
        const d = document.getElementById('daySelect').value;
        const s = d ? `${y}-${m}-${d}` : `${y}-${m}-01`;
        let e;
        if (d) { e = this.formatDate(new Date(new Date(s).getTime() + 86400000)); }
        else {
            let dim = new Date(y, m, 0).getDate();
            e = `${y}-${m}-${dim}`;
        }

        const btn = document.getElementById('exportCsvBtn');
        const originalText = btn ? btn.innerHTML : '匯出';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '⏳ 處理中...';
        }

        try {
            const url = `/expense/api/records/export?start_date=${s}&end_date=${e}`;
            const res = await fetch(url);
            const contentType = res.headers.get('content-type');

            if (contentType && contentType.includes('application/json')) {
                const data = await res.json();
                if (data.success && data.method === 'email') {
                    alert('✅ ' + data.message);
                } else {
                    if (data.error) alert('❌ ' + data.error);
                }
            } else {
                const blob = await res.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                const disposition = res.headers.get('Content-Disposition');
                let filename = 'expense_export.csv';
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
                    if (matches != null && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);
            }
        } catch (error) {
            alert('匯出失敗：網路錯誤');
            console.error(error);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Auto Init: Detect which page we're on
    // Check .today-view FIRST before .expense-dashboard since today page has both classes
    if (document.querySelector('.today-view')) {
        expenseApp.init(); // Use init() since initToday() doesn't exist
    } else if (document.querySelector('.expense-dashboard')) {
        expenseApp.init();
    } else if (document.querySelector('.expense-history')) {
        expenseApp.initHistory();
        loadExpenseTrendChart(); // Load chart on history page
    } else if (document.querySelector('.expense-settings-wrapper')) {
        expenseApp.initSettings();
    }
});

// 載入支出趨勢圖
async function loadExpenseTrendChart() {
    try {
        const response = await fetch('/expense/api/expense-trend');
        const data = await response.json();

        const ctx = document.getElementById('expenseTrendChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: '週期支出',
                    data: data.data,
                    borderColor: '#FF3B30',
                    backgroundColor: 'rgba(255, 59, 48, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#FF3B30',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14 },
                        bodyFont: { size: 13 },
                        callbacks: {
                            title: (ctx) => {
                                const idx = ctx[0].dataIndex;
                                return data.period_details[idx]; // 顯示完整日期範圍
                            },
                            label: (ctx) => `支出: NT$ ${ctx.parsed.y.toLocaleString()}`
                        }
                    },
                    title: {
                        display: true,
                        text: `共 ${data.total_cycles} 個週期的數據`,
                        font: { size: 11 },
                        color: 'rgba(255,255,255,0.5)',
                        padding: { top: 0, bottom: 10 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `$${value.toLocaleString()}`,
                            color: 'rgba(255, 255, 255, 0.7)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        display: false, // 隱藏 X 軸標籤，避免擁擠
                        ticks: { color: 'rgba(255, 255, 255, 0.7)' },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('載入支出趨勢圖失敗:', error);
    }
}


// Add initSettings to object
expenseApp.initSettings = function () {
    this.loadSettings().then(() => {
        this.renderSettingsLists();
    });

    // Handle Category Add
    document.getElementById('addCatBtn').addEventListener('click', () => {
        const name = document.getElementById('newCatName').value.trim();
        const emoji = document.getElementById('newCatEmoji').value.trim();
        const color = document.getElementById('newCatColor').value;
        if (!name) return;

        this.settings.custom_categories.push({ name, emoji, color });
        document.getElementById('newCatName').value = '';
        document.getElementById('newCatEmoji').value = '';
        this.renderSettingsLists();
        this.saveSettings();
    });

    // Handle Recurring Add
    document.getElementById('openAddRecurringBtn').addEventListener('click', () => {
        // Simple prompt flow for V1
        const name = prompt('固定支出名稱 (如: Netflix)');
        if (!name) return;
        const amount = prompt('金額 (如: 390)');
        if (!amount) return;
        const day = prompt('每月幾號扣款? (1-31)');
        if (!day) return;

        this.settings.recurring_expenses.push({
            id: Date.now(),
            name,
            amount: parseInt(amount),
            day: parseInt(day),
            category: '其他' // Default, maybe ask prompt?
        });
        this.renderSettingsLists();
        this.saveSettings();
    });

    // Intercept Submit
    document.getElementById('settingsForm').addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveSettings().then(() => {
            alert('設定已儲存！');
            window.location.reload();
        });
    });
};

expenseApp.saveSettings = async function () {
    // Gather simple inputs from DOM
    const form = document.getElementById('settingsForm');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());

    // Explicitly Add/Overwrite complex objects
    payload.custom_categories = this.settings.custom_categories;
    payload.recurring_expenses = this.settings.recurring_expenses;
    payload.quick_shortcuts = this.settings.quick_shortcuts;

    // Fix numeric types for backend consistency
    if (payload.monthly_budget) payload.monthly_budget = parseFloat(payload.monthly_budget);
    if (payload.billing_cycle_start_day) payload.billing_cycle_start_day = parseInt(payload.billing_cycle_start_day);
    if (payload.editable_month_range) payload.editable_month_range = parseInt(payload.editable_month_range);
    if (payload.budget_alert_threshold) payload.budget_alert_threshold = parseInt(payload.budget_alert_threshold);

    // CLEAN DATA BEFORE SENDING
    payload.custom_categories = (this.settings.custom_categories || []).filter(c => c && c.name);
    payload.recurring_expenses = (this.settings.recurring_expenses || []).filter(r => r && r.name);
    payload.quick_shortcuts = (this.settings.quick_shortcuts || []).filter(s => s && s.name);
    try {
        await fetch('/expense/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        // Optional: show toast
    } catch (e) { console.error('Save failed', e); alert('儲存失敗'); }
};

expenseApp.renderSettingsLists = function () {
    // Categories
    const catList = document.getElementById('categoryList');
    if (catList) {
        catList.innerHTML = '';
        (this.settings.custom_categories || []).forEach((c, idx) => {
            if (!c || !c.name) return;
            const el = document.createElement('div');
            el.className = 'setting-item-row glass';
            el.style.cssText = 'display:flex; justify-content:space-between; padding:12px; margin-bottom:8px; align-items:center;';
            el.innerHTML = `
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="font-size:1.2rem; filter: drop-shadow(0 0 5px ${c.color});">${c.emoji || '🏷️'}</span>
                    <span style="font-weight:500;">${c.name}</span>
                </div>
                <div style="display:flex; gap:15px;">
                    <span class="material-icons" style="color:var(--text-secondary); cursor:pointer;" onclick="expenseApp.editCategory(${idx})">edit</span>
                    <span class="material-icons" style="color:#ef4444; cursor:pointer;" onclick="expenseApp.removeCategory(${idx})">delete</span>
                </div>
            `;
            catList.appendChild(el);
        });
    }

    // Recurring
    const recList = document.getElementById('recurringList');
    if (recList) {
        recList.innerHTML = '';
        (this.settings.recurring_expenses || []).forEach((r, idx) => {
            const el = document.createElement('div');
            el.className = 'setting-item-row glass';
            el.style.cssText = 'display:flex; justify-content:space-between; padding:12px; margin-bottom:8px; align-items:center;';
            el.innerHTML = `
                <div>
                    <div style="font-weight:bold; margin-bottom:2px;">${r.name}</div>
                    <div style="font-size:0.8rem; opacity:0.7;">每月 ${r.day} 號 • $${r.amount}</div>
                </div>
                <div style="display:flex; gap:15px;">
                    <span class="material-icons" style="color:var(--text-secondary); cursor:pointer;" onclick="expenseApp.editRecurring(${idx})">edit</span>
                    <span class="material-icons" style="color:#ef4444; cursor:pointer;" onclick="expenseApp.removeRecurring(${idx})">delete</span>
                </div>
            `;
            recList.appendChild(el);
        });
    }

    // Shortcuts
    const shortList = document.getElementById('shortcutList');
    if (shortList) {
        shortList.innerHTML = '';
        (this.settings.quick_shortcuts || []).forEach((s, idx) => {
            // Handle case where s might be string during migration in memory before save
            const name = typeof s === 'string' ? s : s.name;
            const emoji = typeof s === 'string' ? '⚡' : (s.emoji || '⚡');

            const el = document.createElement('div');
            el.className = 'setting-item-row glass';
            el.style.cssText = 'display:flex; justify-content:space-between; padding:12px; margin-bottom:8px; align-items:center;';
            el.innerHTML = `
                <div style="font-weight:500;">
                    <span style="margin-right:8px;">${emoji}</span>${name}
                </div>
                <div style="display:flex; gap:15px;">
                    <span class="material-icons" style="color:var(--text-secondary); cursor:pointer;" onclick="expenseApp.editShortcut(${idx})">edit</span>
                    <span class="material-icons" style="color:#ef4444; cursor:pointer;" onclick="expenseApp.removeShortcut(${idx})">delete</span>
                </div>
            `;
            shortList.appendChild(el);
        });
    }
};

expenseApp.removeCategory = function (idx) {
    if (!confirm('確定刪除?')) return;
    this.settings.custom_categories.splice(idx, 1);
    this.renderSettingsLists();
    this.saveSettings();
};

expenseApp.removeRecurring = function (idx) {
    if (!confirm('確定刪除?')) return;
    this.settings.recurring_expenses.splice(idx, 1);
    this.renderSettingsLists();
    this.saveSettings();
};

expenseApp.removeShortcut = function (idx) {
    if (!confirm('確定刪除?')) return;
    this.settings.quick_shortcuts.splice(idx, 1);
    this.renderSettingsLists();
    this.saveSettings();
};

expenseApp.editCategory = function (idx) {
    const cat = this.settings.custom_categories[idx];
    const newName = prompt('修改類別名稱:', cat.name);
    if (newName === null) return;
    if (!newName) return alert('名稱不能為空');

    const newEmoji = prompt('修改圖示 (Emoji):', cat.emoji);
    const newColor = prompt('修改顏色 (Hex):', cat.color);

    this.settings.custom_categories[idx] = {
        name: newName,
        emoji: newEmoji || cat.emoji,
        color: newColor || cat.color
    };
    this.renderSettingsLists();
    this.saveSettings();
};

expenseApp.editRecurring = function (idx) {
    const rec = this.settings.recurring_expenses[idx];
    const newName = prompt('修改名稱:', rec.name);
    if (newName === null) return;

    const newAmount = prompt('修改金額:', rec.amount);
    if (newAmount === null) return;

    const newDay = prompt('修改扣款日 (1-31):', rec.day);
    if (newDay === null) return;

    this.settings.recurring_expenses[idx] = {
        ...rec,
        name: newName || rec.name,
        amount: parseInt(newAmount) || rec.amount,
        day: parseInt(newDay) || rec.day
    };
    this.renderSettingsLists();
    this.saveSettings();
};

expenseApp.editShortcut = function (idx) {
    const item = this.settings.quick_shortcuts[idx];
    const oldName = typeof item === 'string' ? item : item.name;
    const oldEmoji = typeof item === 'string' ? '⚡' : item.emoji;

    const newName = prompt('修改快捷名稱:', oldName);
    if (newName === null) return;
    if (!newName) return alert('內容不能為空');

    const newEmoji = prompt('修改 Emoji:', oldEmoji);

    this.settings.quick_shortcuts[idx] = {
        name: newName,
        emoji: newEmoji || oldEmoji
    };
    this.renderSettingsLists();
    this.saveSettings();
};

// Add New Shortcut Handler
document.addEventListener('DOMContentLoaded', () => {
    const addShortBtn = document.getElementById('addShortcutBtn');
    if (addShortBtn) {
        addShortBtn.addEventListener('click', () => {
            const nameInput = document.getElementById('newShortcutName');
            const emojiInput = document.getElementById('newShortcutEmoji'); // Assuming we add this

            const val = nameInput.value.trim();
            // If we don't have emoji input yet, default to empty or specific? 
            // We will add emoji input in HTML next.
            const emoji = emojiInput ? emojiInput.value.trim() : '⚡';

            if (!val) return;

            if (!expenseApp.settings.quick_shortcuts) expenseApp.settings.quick_shortcuts = [];

            // Limit to 5
            if (expenseApp.settings.quick_shortcuts.length >= 5) {
                alert('最多只能設定 5 個快捷摘要，請先刪除舊的再新增。');
                return;
            }

            expenseApp.settings.quick_shortcuts.push({
                name: val,
                emoji: emoji
            });

            nameInput.value = '';
            if (emojiInput) emojiInput.value = '';

            expenseApp.renderSettingsLists();
            expenseApp.saveSettings();
        });
    }
});
