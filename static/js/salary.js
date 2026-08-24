const salaryApp = {
    currentWeekStart: null,
    records: [],
    settings: {},

    init() {
        const dash = document.querySelector('.salary-dashboard');
        if (!dash) return;
        const startDateStr = dash.dataset.startDate;
        this.currentWeekStart = new Date(startDateStr);

        this.bindEvents();
        this.loadSettings().then(() => this.loadWeek());
    },

    async loadSettings() {
        try {
            const res = await fetch('/salary/api/settings');
            this.settings = await res.json();
            await this.loadCompaniesForModal();
        } catch (e) { console.error('Failed to load settings', e); }
    },

    async loadCompaniesForModal() {
        try {
            const res = await fetch('/salary/api/companies');
            if (!res.ok) return;
            const companies = await res.json();
            const sel = document.getElementById('recordCompany');
            if (!sel) return;
            sel.innerHTML = companies.map(c => `<option value="${c.id}" data-color="${c.color}" data-rate="${c.hourly_rate}">${c.name}</option>`).join('');

            // Auto-fill rate when company changes
            sel.addEventListener('change', () => {
                const opt = sel.options[sel.selectedIndex];
                const rateInput = document.getElementById('shiftRate');
                if (opt && opt.dataset.rate && rateInput && !rateInput.value) {
                    rateInput.placeholder = `公司時薪 $${opt.dataset.rate}/hr`;
                } else if (rateInput) {
                    rateInput.placeholder = '留空則使用預設時薪';
                }
            });
        } catch(e) { console.warn('Company load failed', e); }
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
        addSafeListener('exportSalaryBtn', 'click', () => this.handleExport());

        // Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Close modal on outside click
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) this.closeModal();
        });

        this.updateActionButtonsVisibility();
    },

    updateActionButtonsVisibility() {
        const dash = document.querySelector('.salary-dashboard');
        if (!dash) return;
        const isPast = !this.isDateEditable(this.formatDate(this.currentWeekStart));
        const copyBtn = document.getElementById('copyLastWeekBtn');
        const clearBtn = document.getElementById('clearThisWeekBtn');

        if (copyBtn) copyBtn.style.display = isPast ? 'none' : 'inline-flex';
        if (clearBtn) clearBtn.style.display = isPast ? 'none' : 'inline-flex';
    },

    getActivePeriod() {
        // Standard Month: Editable from 1st of PREVIOUS month (default)
        // Settings: 0=Current, 1=Prev, -1=Unlimited
        const range = this.settings.editable_month_range !== undefined ? this.settings.editable_month_range : 1;

        const now = new Date();
        let offset = 0;

        if (range === -1) {
            // Unlimited: Set to very old date
            return { start: new Date(2000, 0, 1) };
        } else {
            offset = range;
        }

        const start = new Date(now.getFullYear(), now.getMonth() - offset, 1);
        return { start };
    },


    isDateEditable(dateStr) {
        const period = this.getActivePeriod();
        const date = new Date(dateStr);
        return date >= period.start;
    },

    async loadWeek() {
        if (!this.currentWeekStart) return;
        const startStr = this.formatDate(this.currentWeekStart);
        const end = new Date(this.currentWeekStart);
        end.setDate(end.getDate() + 6);
        const endStr = this.formatDate(end);

        const label = document.getElementById('currentWeekLabel');
        if (label) {
            label.textContent = `${startStr.replace(/-/g, '/')} - ${endStr.slice(5).replace(/-/g, '/')}`;
        }

        try {
            const response = await fetch(`/salary/api/records?start_date=${startStr}&end_date=${endStr}`);
            this.records = await response.json();
            this.renderGrid();
            this.updateSummary();
            this.updateMonthlyGoalForWeek();
        } catch (error) {
            console.error('Error loading data:', error);
        }
    },

    renderGrid() {
        document.querySelectorAll('.shifts-container').forEach(el => el.innerHTML = '');
        const todayStr = this.formatDate(new Date());

        for (let i = 0; i < 7; i++) {
            const currentDay = new Date(this.currentWeekStart);
            currentDay.setDate(this.currentWeekStart.getDate() + i);
            const dateStr = this.formatDate(currentDay);

            const col = document.querySelector(`.day-column[data-day-index="${i}"]`);
            if (!col) continue;

            col.querySelector('.day-date').textContent = `${currentDay.getMonth() + 1}/${currentDay.getDate()}`;

            if (dateStr === todayStr) col.classList.add('today');
            else col.classList.remove('today');

            const dayRecords = this.records.filter(r => r.date === dateStr);
            const container = col.querySelector('.shifts-container');
            const addBtn = col.querySelector('.btn-add-shift');

            if (addBtn) {
                addBtn.style.display = this.isDateEditable(dateStr) ? 'flex' : 'none';
            }

            dayRecords.forEach(record => {
                const card = document.createElement('div');
                card.className = `shift-card ${record.type === 'bonus' ? 'bonus' : ''}`;
                if (record.company_color) {
                    card.style.borderLeftColor = record.company_color;
                }
                card.onclick = () => this.openEditModal(record);

                if (record.type === 'shift') {
                    card.innerHTML = `
                        <div class="shift-time">${record.start_time} - ${record.end_time}</div>
                        <div class="shift-info">
                            <span>${record.hours}h</span>
                            <span>$${Math.round(record.amount)}</span>
                        </div>
                        ${record.company_name ? `<div style="font-size:0.72rem;color:${record.company_color || 'var(--text-secondary)'};margin-top:2px;">${record.company_name}</div>` : ''}
                    `;
                } else {
                    card.innerHTML = `
                        <div class="shift-time" style="color:#ffd700">💰 獎金 $${record.amount}</div>
                        <div class="shift-info">
                            <span>${record.note || ''}</span>
                        </div>
                        ${record.company_name ? `<div style="font-size:0.72rem;color:${record.company_color || 'var(--text-secondary)'};margin-top:2px;">${record.company_name}</div>` : ''}
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

        const hEl = document.getElementById('weeklyHours');
        const aEl = document.getElementById('weeklyAmount');
        if (hEl) hEl.textContent = `${hours.toFixed(1)}h`;
        if (aEl) aEl.textContent = `$${Math.round(amount)}`;
        
        this.renderCompanyBreakdown(this.records);
    },

    renderCompanyBreakdown(records) {
        const container = document.getElementById('companyBreakdownContainer');
        const barContainer = document.getElementById('companyBreakdownBar');
        const listContainer = document.getElementById('companyBreakdownList');
        
        if (!container || !barContainer || !listContainer) return;

        // Group by company
        const compStats = {};
        let totalAmount = 0;

        records.forEach(r => {
            const cid = r.company_id || 'unassigned';
            if (!compStats[cid]) {
                compStats[cid] = {
                    name: r.company_name || '未指定公司',
                    color: r.company_color || '#9ca3af',
                    hours: 0,
                    amount: 0
                };
            }
            if (r.type === 'shift') {
                compStats[cid].hours += r.hours;
            }
            compStats[cid].amount += r.amount;
            totalAmount += r.amount;
        });

        const statsArray = Object.values(compStats).filter(s => s.amount > 0).sort((a, b) => b.amount - a.amount);

        if (statsArray.length === 0 || totalAmount === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        
        // Render Bar
        barContainer.innerHTML = statsArray.map(s => {
            const pct = (s.amount / totalAmount * 100).toFixed(1);
            return `<div style="width: ${pct}%; height: 100%; background: ${s.color};" title="${s.name} ${pct}%"></div>`;
        }).join('');

        // Render List
        // Override inline grid styles from HTML to use flexible wrapping
        listContainer.style.display = 'flex';
        listContainer.style.flexWrap = 'wrap';
        listContainer.style.gap = '12px';
        
        listContainer.innerHTML = statsArray.map(s => {
            const pct = (s.amount / totalAmount * 100).toFixed(1);
            return `
                <div style="display: flex; justify-content: space-between; align-items: center; flex: 1 1 250px; max-width: 400px; background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; white-space: nowrap;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: ${s.color}; flex-shrink: 0;"></div>
                        <span style="font-weight: 500;">${s.name}</span>
                        <span style="color: var(--text-secondary); font-size: 0.8rem;">${pct}%</span>
                    </div>
                    <div style="text-align: right; white-space: nowrap; margin-left: 16px;">
                        <span style="margin-right: 12px; color: var(--text-secondary); font-size: 0.85rem;">${s.hours.toFixed(1)}h</span>
                        <span style="font-weight: 600;">$${Math.round(s.amount)}</span>
                    </div>
                </div>
            `;
        }).join('');
    },

    async updateMonthlyGoalForWeek() {
        if (!this.currentWeekStart) return;
        // Determine the month of the current week start
        const y = this.currentWeekStart.getFullYear();
        const m = this.currentWeekStart.getMonth();
        const start = this.formatDate(new Date(y, m, 1));
        const end = this.formatDate(new Date(y, m + 1, 0)); // Last day of month

        try {
            // Fetch all records for this month to calculate total
            const res = await fetch(`/salary/api/records?start_date=${start}&end_date=${end}`);
            const data = await res.json();
            const total = data.reduce((sum, r) => sum + r.amount, 0);
            this.updateTargetProgress(total);
        } catch (e) { console.error(e); }
    },

    updateTargetProgress(currentAmount) {
        const targetContainer = document.getElementById('targetIncomeContainer');
        if (targetContainer && this.settings.target_income > 0) {
            targetContainer.style.display = 'block';
            const percent = Math.min(100, (currentAmount / this.settings.target_income) * 100);

            const bar = document.getElementById('targetIncomeBar');
            const txt = document.getElementById('targetIncomePercent');

            if (bar) bar.style.width = `${percent}%`;
            if (txt) txt.textContent = `${percent.toFixed(1)}%`;

            // Color logic
            if (bar) {
                if (percent >= 100) bar.style.background = '#4ade80'; // Success
                else bar.style.background = 'var(--accent-color)';
            }
        } else if (targetContainer) {
            targetContainer.style.display = 'none';
        }
    },

    changeWeek(days) {
        this.currentWeekStart.setDate(this.currentWeekStart.getDate() + days);
        this.updateActionButtonsVisibility();
        this.loadWeek();
    },

    goToToday() {
        const now = new Date();
        const day = now.getDay() || 7;
        now.setDate(now.getDate() - day + 1);
        this.currentWeekStart = now;
        this.updateActionButtonsVisibility();
        this.loadWeek();
    },

    openAddModal(dayIndex) {
        const targetDate = new Date(this.currentWeekStart);
        targetDate.setDate(targetDate.getDate() + dayIndex);

        if (!this.isDateEditable(this.formatDate(targetDate))) return;


        this.resetForm();
        document.getElementById('recordDate').value = this.formatDate(targetDate);
        document.getElementById('modalTitle').textContent = `新增紀錄 (${targetDate.getMonth() + 1}/${targetDate.getDate()})`;
        document.getElementById('deleteBtn').classList.add('hidden');

        // Ensure editable state reset
        document.querySelectorAll('#recordForm input').forEach(el => {
            if (el.type !== 'hidden') {
                el.readOnly = false;
                el.disabled = false;
            }
        });
        const submitBtn = document.querySelector('#recordForm button[type="submit"]');
        if (submitBtn) submitBtn.classList.remove('hidden');

        this.switchTab('shift');
        const tabs = document.querySelector('.tabs');
        if (tabs) tabs.classList.remove('hidden');

        document.getElementById('recordModal').classList.add('show');
    },

    openEditModal(record) {
        const isEditable = this.isDateEditable(record.date);

        document.getElementById('recordId').value = record.id;
        document.getElementById('recordDate').value = record.date;
        document.getElementById('recordType').value = record.type;
        document.getElementById('modalTitle').textContent = isEditable ? '編輯紀錄' : '查看紀錄 (唯讀)';

        const deleteBtn = document.getElementById('deleteBtn');
        const submitBtn = document.querySelector('#recordForm button[type="submit"]');

        if (deleteBtn) deleteBtn.classList.toggle('hidden', !isEditable || !record.id);
        if (submitBtn) submitBtn.classList.toggle('hidden', !isEditable);

        const formElements = document.querySelectorAll('#recordForm input, #recordForm select, #recordForm textarea');
        formElements.forEach(el => {
            if (el.type !== 'hidden') {
                el.readOnly = !isEditable;
                el.disabled = !isEditable;
            }
        });

        const tabs = document.querySelector('.tabs');
        if (tabs) tabs.classList.toggle('hidden', !isEditable || !!record.id);

        if (record.type === 'shift') {
            this.switchTab('shift');
            document.getElementById('startTime').value = record.start_time;
            document.getElementById('endTime').value = record.end_time;
            document.getElementById('shiftRate').value = record.rate || '';
        } else {
            this.switchTab('bonus');
            document.getElementById('bonusAmount').value = record.amount;
            document.getElementById('bonusNote').value = record.note || '';
            const hoursField = document.getElementById('bonusHours');
            if (hoursField) hoursField.value = record.hours || '';
        }

        // Set company
        const companySel = document.getElementById('recordCompany');
        if (companySel) companySel.value = record.company_id || '';

        document.getElementById('recordModal').classList.add('show');
    },

    refreshData() {
        if (document.querySelector('.salary-dashboard')) {
            this.loadWeek();
        } else if (document.querySelector('.salary-monthly')) {
            this.loadMonth();
        } else if (document.querySelector('.salary-history')) {
            this.loadHistoryData();
        }
    },

    closeModal() {
        document.getElementById('recordModal').classList.remove('show');
    },

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(`${tabName}-tab`);

        if (activeBtn) activeBtn.classList.add('active');
        if (activeContent) {
            activeContent.classList.add('active');
            activeContent.querySelectorAll('input, select, textarea').forEach(input => {
                if (!document.getElementById('modalTitle').textContent.includes('唯讀')) {
                    input.disabled = false;
                }
            });
            
            // Move company selector to the active tab
            const companyGroup = document.getElementById('companyGroup');
            if (companyGroup) {
                if (tabName === 'shift') {
                    const shiftRate = document.getElementById('shiftRate');
                    if (shiftRate && shiftRate.closest('.form-group')) {
                        shiftRate.closest('.form-group').before(companyGroup);
                    }
                } else if (tabName === 'bonus') {
                    activeContent.prepend(companyGroup);
                }
            }
        }
        document.getElementById('recordType').value = tabName;
    },

    resetForm() {
        document.getElementById('recordForm').reset();
        document.getElementById('recordId').value = '';
        document.getElementById('startTime').value = this.settings.default_start_time || '09:00';
        document.getElementById('endTime').value = this.settings.default_end_time || '18:00';
        const rateInput = document.getElementById('shiftRate');
        if (rateInput) rateInput.value = '';
        const companySel = document.getElementById('recordCompany');
        if (companySel) {
            companySel.value = '';
            // Select the first available company by default if options exist
            if (companySel.options.length > 0) {
                companySel.selectedIndex = 0;
            }
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        const id = data.id;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/salary/api/records/${id}` : '/salary/api/records';

        if (data.type === 'shift') {
            if (data.start_time >= data.end_time) {
                alert('結束時間必須晚於開始時間');
                return;
            }
            // Logic handled by backend now, but let's be clean
            delete data.hours;
            if (data.rate === '') delete data.rate;
        } else {
            // Bonus mode
            if (data.hours === '') delete data.hours;
            else data.hours = parseFloat(data.hours);

            if (data.amount === '') data.amount = 0;
            else data.amount = parseFloat(data.amount);
        }

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                this.closeModal();
                this.refreshData();
            } else {
                const err = await res.json();
                alert(err.error || '儲存失敗');
            }
        } catch (error) {
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
                this.refreshData();
            }
        } catch (error) {
            console.error(error);
        }
    },

    async copyLastWeek() {
        if (!confirm('確定要複製上週的班表到本週嗎？')) return;
        const targetDate = this.formatDate(this.currentWeekStart);

        try {
            const res = await fetch('/salary/api/actions/copy_week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_date: targetDate })
            });

            if (res.ok) {
                const data = await res.json();
                alert(`已複製 ${data.count} 筆紀錄`);
                this.loadWeek();
            }
        } catch (error) { }
    },

    async handleExport() {
        const btn = document.getElementById('exportSalaryBtn');
        const originalText = btn ? btn.innerHTML : '匯出';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '⏳ 處理中...';
        }

        try {
            const res = await fetch('/salary/api/export');
            const data = await res.json();
            
            if (data.success) {
                if (data.message) alert('✅ ' + data.message);
                
                if (data.csv_content) {
                    const blob = new Blob(['\ufeff' + data.csv_content], { type: 'text/csv;charset=utf-8-sig' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = data.filename || 'salary_export.csv';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                }
            } else {
                if (data.error) alert('❌ ' + data.error);
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
    },

    async handlePeriodExport() {
        const select = document.getElementById('periodSelect');
        const period = select ? select.value : '';
        if (!period) { alert('請先選擇匯出週期'); return; }

        const btn = document.getElementById('exportPeriodBtn');
        const originalText = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '⏳ 處理中...'; }

        try {
            const res = await fetch(`/salary/api/export-period?period=${encodeURIComponent(period)}`);
            const data = await res.json();

            if (data.success) {
                if (data.message) alert('✅ ' + data.message);
                
                if (data.csv_content) {
                    const blob = new Blob(['\ufeff' + data.csv_content], { type: 'text/csv;charset=utf-8-sig' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = data.filename || `salary_${period}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                }
            } else {
                if (data.error) alert('❌ ' + data.error);
            }
        } catch (err) {
            alert('匯出失敗：網路錯誤');
            console.error(err);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
        }
    },

    async clearThisWeek() {
        if (!confirm('確定要清空本週的所有排班與獎金嗎？')) return;
        const weekStart = this.formatDate(this.currentWeekStart);

        try {
            const res = await fetch('/salary/api/actions/clear_week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week_start: weekStart })
            });

            if (res.ok) {
                this.loadWeek();
            }
        } catch (error) { }
    },

    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

    // Monthly View
    initMonthly() {
        const now = new Date();
        this.currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        this.holidays = {};   // { 'YYYY-MM-DD': '假日名稱' }
        this.bindEvents();
        this.loadSettings().then(() => this.loadMonth());
    },

    changeMonth(delta) {
        this.currentMonth.setMonth(this.currentMonth.getMonth() + delta);
        this.loadMonth();
    },

    async loadMonth() {
        const y = this.currentMonth.getFullYear();
        const m = this.currentMonth.getMonth();
        const label = document.getElementById('currentMonthLabel');
        if (label) label.textContent = `${y}年 ${String(m + 1).padStart(2, '0')}月`;

        const firstDay = new Date(y, m, 1);
        const gridStart = new Date(firstDay);
        gridStart.setDate(1 - (firstDay.getDay() || 7) + 1);

        try {
            // Fetch shift records AND holidays in parallel
            const [recRes, holRes] = await Promise.all([
                fetch(`/salary/api/records?start_date=${this.formatDate(gridStart)}&end_date=${this.formatDate(new Date(gridStart.getTime() + 42 * 864e5))}`),
                fetch(`/salary/api/holidays?year=${y}`)
            ]);
            this.records = await recRes.json();
            this.holidays = holRes.ok ? await holRes.json() : {};
            this.renderCalendar(gridStart);

            // Cycle: 1st ~ Last Day of Month (Standard)
            const cycleStart = new Date(y, m, 1);
            // End date (exclusive for calculation) is 1st of next month
            const nextMonth = new Date(y, m + 1, 1);
            // Last day for display (inclusive)
            const cycleEndDisplay = new Date(nextMonth);
            cycleEndDisplay.setDate(cycleEndDisplay.getDate() - 1);


            // Adjust label to show cycle clearly
            const summaryCard = document.querySelector('.summary-card');
            if (summaryCard) {
                let rangeDisplay = summaryCard.querySelector('.range-display');
                if (!rangeDisplay) {
                    rangeDisplay = document.createElement('div');
                    rangeDisplay.className = 'range-display';
                    summaryCard.appendChild(rangeDisplay);
                }
                // Format: 1/1 ~ 1/31
                rangeDisplay.textContent = `${cycleStart.getMonth() + 1}/${cycleStart.getDate()} ~ ${cycleEndDisplay.getMonth() + 1}/${cycleEndDisplay.getDate()}`;
            }

            // Calculations use [start, end) logic usually, or inclusive check
            // We pass (start, nextMonth) to be used as < nextMonth
            this.updateMonthlySummary(cycleStart, nextMonth);

            // Also update tooltip
            const hLabel = document.querySelector('.summary-item:first-child .label');
            if (hLabel) hLabel.setAttribute('title', `${this.formatDate(cycleStart)} ~ ${this.formatDate(cycleEndDisplay)}`);
        } catch (error) { }
    },

    renderCalendar(startDate) {
        const container = document.getElementById('calendarBody');
        if (!container) return;
        container.innerHTML = '';
        const todayStr = this.formatDate(new Date());

        for (let i = 0; i < 42; i++) {
            const current = new Date(startDate);
            current.setDate(startDate.getDate() + i);
            const dateStr = this.formatDate(current);
            const holidayName = (this.holidays || {})[dateStr];

            const cell = document.createElement('div');
            let cellClass = `calendar-day ${current.getMonth() !== this.currentMonth.getMonth() ? 'other-month' : ''} ${dateStr === todayStr ? 'today' : ''}`;
            if (holidayName) cellClass += ' holiday';
            cell.className = cellClass;

            const header = document.createElement('div');
            header.className = 'cal-day-header';
            header.textContent = current.getDate();

            // Holiday badge inside header
            if (holidayName) {
                const badge = document.createElement('span');
                badge.className = 'holiday-badge';
                badge.textContent = holidayName;
                header.appendChild(badge);
            }

            cell.appendChild(header);

            const content = document.createElement('div');
            content.className = 'cal-day-content';

            if (this.isDateEditable(dateStr)) {
                cell.onclick = () => this.openAddModalForDate(new Date(current));
            }

            const dayRecords = this.records.filter(r => r.date === dateStr);
            dayRecords.forEach(r => {
                const item = document.createElement('div');
                item.className = 'cal-item';
                const isHolidayShift = r.type === 'shift' && holidayName;
                
                let text = r.type === 'shift' ? `${r.start_time}${isHolidayShift ? ' ×2' : ''}` : `💰 獎金`;
                
                item.innerHTML = `
                    <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:${r.company_color || 'var(--text-secondary)'}; margin-right:4px;"></span>
                    <span>${text}</span>
                `;
                
                if (r.type === 'bonus') item.style.color = '#ffd700';
                if (isHolidayShift) item.style.color = '#f87171';
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
        if (!this.isDateEditable(this.formatDate(date))) return;

        this.resetForm();

        const dateStr = this.formatDate(date);
        const holidayName = (this.holidays || {})[dateStr];

        document.getElementById('recordDate').value = dateStr;
        let titleText = `新增紀錄 (${date.getMonth() + 1}/${date.getDate()})`;
        if (holidayName) titleText += ` 🎌 ${holidayName}（國定假日，薪水自動加倍）`;
        document.getElementById('modalTitle').textContent = titleText;

        document.querySelectorAll('#recordForm input').forEach(el => {
            if (el.type !== 'hidden') {
                el.readOnly = false;
                el.disabled = false;
            }
        });
        const submitBtn = document.querySelector('#recordForm button[type="submit"]');
        if (submitBtn) submitBtn.classList.remove('hidden');

        this.switchTab('shift');
        const tabs = document.querySelector('.tabs');
        if (tabs) tabs.classList.remove('hidden');
        document.getElementById('recordModal').classList.add('show');
    },

    updateMonthlySummary(start, end) {
        const startStr = this.formatDate(start);
        const endStr = this.formatDate(end);
        let hours = 0, amount = 0;
        let filteredRecords = [];

        this.records.forEach(r => {
            // Logic: start <= date < end (e.g. Jan 10 <= date < Feb 10)
            if (r.date >= startStr && r.date < endStr) {
                if (r.type === 'shift') hours += r.hours;
                amount += r.amount;
                filteredRecords.push(r);
            }
        });

        const hEl = document.getElementById('monthlyHours');
        const aEl = document.getElementById('monthlyAmount');
        if (hEl) hEl.textContent = `${hours.toFixed(1)}h`;
        if (aEl) aEl.textContent = `$${Math.round(amount)}`;

        this.updateTargetProgress(amount);
        this.renderCompanyBreakdown(filteredRecords);
    },

    // History
    initHistory() {
        this.bindEvents();
        const select = document.getElementById('periodSelect');
        if (select) {
            select.addEventListener('change', () => this.loadHistoryData());

            // Period navigation
            const prevBtn = document.getElementById('prevPeriodBtn');
            const nextBtn = document.getElementById('nextPeriodBtn');
            // 因為後端反轉了列表（最新在 index 0），所以「上一期」是往舊的找（index + 1），「下一期」是往新的找（index - 1）
            if (prevBtn) prevBtn.addEventListener('click', () => this.changeHistoryPeriod(1));
            if (nextBtn) nextBtn.addEventListener('click', () => this.changeHistoryPeriod(-1));

            // Period export
            const exportPeriodBtn = document.getElementById('exportPeriodBtn');
            if (exportPeriodBtn) exportPeriodBtn.addEventListener('click', () => this.handlePeriodExport());

            this.loadSettings().then(() => this.loadHistoryPeriods());
        }
    },

    changeHistoryPeriod(delta) {
        const select = document.getElementById('periodSelect');
        if (!select || select.options.length === 0) return;

        const currentIndex = select.selectedIndex;
        const newIndex = currentIndex + delta;

        if (newIndex >= 0 && newIndex < select.options.length) {
            select.selectedIndex = newIndex;
            this.loadHistoryData();
        }
    },

    async loadHistoryPeriods() {
        try {
            const res = await fetch('/salary/api/history/periods');
            const periods = await res.json();
            const select = document.getElementById('periodSelect');
            select.innerHTML = '';

            if (periods.length === 0) {
                select.innerHTML = '<option>無資料</option>';
                return;
            }

            const todayStr = this.formatDate(new Date());
            periods.forEach(p => {
                const opt = document.createElement('option');
                opt.value = `${p.start},${p.end}`;
                opt.textContent = p.label;
                select.appendChild(opt);
                if (todayStr >= p.start && todayStr <= p.end) select.value = opt.value;
            });

            this.loadHistoryData();
        } catch (error) { }
    },

    async loadHistoryData() {
        const select = document.getElementById('periodSelect');
        if (!select || !select.value) return;
        const [start, end] = select.value.split(',');

        try {
            const res = await fetch(`/salary/api/history/data?start_date=${start}&end_date=${end}`);
            const data = await res.json();

            document.getElementById('historyHours').textContent = `${data.total_hours.toFixed(1)}h`;
            document.getElementById('historyAmount').textContent = `$${Math.round(data.total_amount)}`;
            document.getElementById('historyCount').textContent = data.record_count;

            this.updateTargetProgress(data.total_amount);
            this.renderCompanyBreakdown(data.records);

            const tbody = document.getElementById('historyTableBody');
            tbody.innerHTML = '';
            data.records.sort((a, b) => a.date < b.date ? 1 : -1);

            data.records.forEach(r => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.onclick = () => this.openEditModal(r);
                
                const companyHtml = r.company_name 
                    ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${r.company_color};margin-right:4px;"></span><span style="color:var(--text-secondary);font-size:0.85em;">${r.company_name}</span>`
                    : '';
                    
                tr.innerHTML = r.type === 'shift' ? `
                    <td>${r.date}</td><td>排班</td><td>${r.start_time} - ${r.end_time}<br>${companyHtml}</td><td>${r.hours}</td><td>${r.rate}/hr -> $${Math.round(r.amount)}</td><td>${r.note || ''}</td>
                ` : `
                    <td>${r.date}</td><td style="color:#ffd700">獎金</td><td>${companyHtml}</td><td>${r.hours || ''}</td><td>$${r.amount}</td><td>${r.note || ''}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (error) { }
    },

    initSettings() {
        const form = document.getElementById('settingsForm');
        if (!form) return;

        // --- Status badge helper ---
        const statusEl = document.getElementById('settings-save-status');
        const setStatus = (state) => {
            if (!statusEl) return;
            const map = {
                saving: { text: '儲存中…', cls: 'status-saving' },
                saved: { text: '✓ 已儲存', cls: 'status-saved' },
                error: { text: '✗ 儲存失敗', cls: 'status-error' },
                idle: { text: '', cls: '' }
            };
            statusEl.textContent = map[state].text;
            statusEl.className = 'settings-save-status ' + map[state].cls;
        };

        // --- Core save function ---
        const doSave = async () => {
            setStatus('saving');
            const data = Object.fromEntries(new FormData(form).entries());
            try {
                const res = await fetch('/salary/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    setStatus('saved');
                    setTimeout(() => setStatus('idle'), 2500);
                } else {
                    setStatus('error');
                }
            } catch (e) {
                setStatus('error');
            }
        };

        // --- Debounce wrapper (800ms) ---
        let debounceTimer;
        const debouncedSave = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(doSave, 800);
        };

        // --- Attach listeners to all inputs ---
        form.querySelectorAll('input, select, textarea').forEach(el => {
            // For text/number: use 'input' (fires on every keystroke)
            el.addEventListener('input', debouncedSave);
            // For select/time: also use 'change' (fires immediately on pick)
            el.addEventListener('change', debouncedSave);
        });

        // --- Keep submit button for explicit save (no page reload) ---
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearTimeout(debounceTimer);
            await doSave();
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.salary-dashboard')) salaryApp.init();
    else if (document.querySelector('.salary-monthly')) salaryApp.initMonthly();
    else if (document.querySelector('.salary-history')) salaryApp.initHistory();
    else if (document.querySelector('.settings-container')) salaryApp.initSettings();

    // Load salary trend chart if on history page
    if (document.getElementById('salaryTrendChart')) {
        loadSalaryTrendChart();
    }
});

// 載入薪資趨勢圖
async function loadSalaryTrendChart() {
    try {
        const response = await fetch('/salary/api/income-trend');
        const data = await response.json();

        const ctx = document.getElementById('salaryTrendChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: '月收入',
                    data: data.data,
                    borderColor: '#FFD60A',
                    backgroundColor: 'rgba(255, 214, 10, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#FFD60A',
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
                            label: (ctx) => `總收入: NT$ ${ctx.parsed.y.toLocaleString()}`,
                            afterBody: (context) => {
                                const index = context[0].dataIndex;
                                const details = data.company_details ? data.company_details[index] : null;
                                if (!details || Object.keys(details).length === 0) return [];
                                
                                const sortedDetails = Object.entries(details).sort((a, b) => b[1] - a[1]);
                                const lines = [''];
                                lines.push('【各公司明細】');
                                for (const [company, amount] of sortedDetails) {
                                    lines.push(`  • ${company}: NT$ ${Math.round(amount).toLocaleString()}`);
                                }
                                return lines;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: `共 ${data.total_months} 個月的數據`,
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
                        display: true,
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.5)',
                            maxRotation: 45,
                            minRotation: 45,
                            maxTicksLimit: 12
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('載入薪資趨勢圖失敗:', error);
    }
}
