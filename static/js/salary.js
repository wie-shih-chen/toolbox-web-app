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
            sel.innerHTML = companies.map(c => `<option value="${c.id}" data-color="${c.color}" data-rate="${c.hourly_rate}" data-start="${c.default_start_time || ''}" data-end="${c.default_end_time || ''}">${c.name}</option>`).join('');

            // Auto-fill rate and times when company changes
            sel.addEventListener('change', () => {
                const opt = sel.options[sel.selectedIndex];
                
                // Rate
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
            this.currentDay   = new Date(n.getFullYear(), n.getMonth(), n.getDate());
            this.currentWeekMonday = this._getMondayOf(n);
            this.currentYear  = n.getFullYear();
            this.loadCurrentView ? this.loadCurrentView() : this.loadMonth();
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
                    let badges = '';
                    const noteStr = record.note || '';
                    if (noteStr.includes('國定假日')) {
                        badges += '<span style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px;">🏮 國定假日</span>';
                    }
                    if (noteStr.includes('勞基法加班')) {
                        badges += '<span style="background: rgba(245, 158, 11, 0.2); color: #fcd34d; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px;">🔥 勞基法加班</span>';
                    }

                    card.innerHTML = `
                        <div class="shift-time">${record.start_time} - ${record.end_time}</div>
                        <div class="shift-info">
                            <span>${record.hours}h</span>
                            <span>$${Math.round(record.amount)}</span>
                        </div>
                        ${record.company_name ? `<div style="font-size:0.72rem;color:${record.company_color || 'var(--text-secondary)'};margin-top:2px;">${record.company_name}</div>` : ''}
                        ${badges ? `<div style="margin-top: 6px;">${badges}</div>` : ''}
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
        // Use CSS classes defined in salary.css for responsive layout
        listContainer.className = 'company-breakdown-list';
        listContainer.style = ''; // clear inline styles from older versions
        
        listContainer.innerHTML = statsArray.map(s => {
            const pct = (s.amount / totalAmount * 100).toFixed(1);
            return `
                <div class="company-breakdown-item">
                    <div class="company-breakdown-name">
                        <div class="company-dot" style="background: ${s.color};"></div>
                        <span class="name-text">${s.name}</span>
                        <span class="pct-text">${pct}%</span>
                    </div>
                    <div class="company-breakdown-stats">
                        <span class="hours-text">${s.hours.toFixed(1)}h</span>
                        <span class="amount-text">$${Math.round(s.amount)}</span>
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
            this.loadCurrentView ? this.loadCurrentView() : this.loadMonth();
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
            
            const lastCompanyId = localStorage.getItem('salary_last_company_id');
            let found = false;
            
            if (lastCompanyId) {
                for (let i = 0; i < companySel.options.length; i++) {
                    if (companySel.options[i].value === lastCompanyId) {
                        companySel.selectedIndex = i;
                        found = true;
                        break;
                    }
                }
            }
            
            if (!found && companySel.options.length > 0) {
                companySel.selectedIndex = 0;
            }
            
            companySel.dispatchEvent(new Event('change'));
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
            if (data.start_time === data.end_time) {
                alert('開始時間與結束時間不能相同');
                return;
            }

            // Clash Detection
            const toEpoch = (dateStr, timeStr) => {
                const [y, m, d] = dateStr.split('-');
                const [H, M] = timeStr.split(':');
                return new Date(y, m-1, d, H, M).getTime();
            };
            const getRange = (dateStr, startStr, endStr) => {
                let s = toEpoch(dateStr, startStr);
                let e = toEpoch(dateStr, endStr);
                if (e < s) e += 24 * 3600 * 1000;
                return [s, e];
            };

            const [newS, newE] = getRange(data.date, data.start_time, data.end_time);
            
            const clashes = this.records.filter(r => {
                if (id && r.id == id) return false;
                if (r.type !== 'shift') return false;
                if (!r.start_time || !r.end_time) return false;
                
                // Only check records around the same date to save perf
                if (Math.abs(new Date(r.date) - new Date(data.date)) > 2 * 24 * 3600 * 1000) return false;

                const [rS, rE] = getRange(r.date, r.start_time, r.end_time);
                return Math.max(newS, rS) < Math.min(newE, rE);
            });

            if (clashes.length > 0) {
                if (!confirm('警告：此時段與現有的班表重疊，確定要儲存嗎？')) {
                    return;
                }
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
                if (data.company_id) {
                    localStorage.setItem('salary_last_company_id', data.company_id);
                }
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

    // ═══════════════════════════════════════════════
    //  Monthly / Multi-View Calendar
    // ═══════════════════════════════════════════════
    initMonthly() {
        const now = new Date();
        this.currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        this.currentDay   = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        this.currentWeekMonday = this._getMondayOf(now);
        this.currentYear  = now.getFullYear();
        this.currentView  = 'month';   // day | week | month | year | schedule
        this.holidays     = {};
        this.bindEvents();

        // View switcher buttons
        document.querySelectorAll('.cal-view-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchView(btn.dataset.view));
        });

        this.loadSettings().then(() => this.loadCurrentView());
    },

    _getMondayOf(date) {
        const d = new Date(date);
        const day = d.getDay() || 7;   // 0(Sun)→7
        d.setDate(d.getDate() - day + 1);
        d.setHours(0,0,0,0);
        return d;
    },

    switchView(mode) {
        this.currentView = mode;
        // Update tab active state
        document.querySelectorAll('.cal-view-btn').forEach(b => b.classList.toggle('active', b.dataset.view === mode));
        // Show/hide view bodies
        // Show/hide view bodies — must use explicit display value, not '' (which falls back to CSS display:none)
        const ids = ['monthViewBody','weekViewBody','dayViewBody','yearViewBody','scheduleViewBody'];
        const map = { month:'monthViewBody', week:'weekViewBody', day:'dayViewBody', year:'yearViewBody', schedule:'scheduleViewBody' };
        const displayVal = { monthViewBody:'flex', weekViewBody:'block', dayViewBody:'block', yearViewBody:'block', scheduleViewBody:'block' };
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = (id === map[mode]) ? displayVal[id] : 'none';
        });

        this.updateNavLabel();
        this.loadCurrentView();
    },

    updateNavLabel() {
        const label = document.getElementById('currentMonthLabel');
        const prev  = document.getElementById('prevMonthBtn');
        const next  = document.getElementById('nextMonthBtn');
        if (!label) return;
        const fmt = (y, m) => `${y}年 ${String(m+1).padStart(2,'0')}月`;
        switch (this.currentView) {
            case 'day': {
                const d = this.currentDay;
                label.textContent = `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
                if (prev) prev.title = '上一天';
                if (next) next.title = '下一天';
                break;
            }
            case 'week': {
                const ws = this.currentWeekMonday;
                const we = new Date(ws); we.setDate(we.getDate()+6);
                label.textContent = `${ws.getMonth()+1}/${ws.getDate()} – ${we.getMonth()+1}/${we.getDate()}`;
                if (prev) prev.title = '上一週';
                if (next) next.title = '下一週';
                break;
            }
            case 'year':
                label.textContent = `${this.currentYear}年`;
                if (prev) prev.title = '上一年';
                if (next) next.title = '下一年';
                break;
            case 'schedule': {
                const m = this.currentMonth;
                label.textContent = fmt(m.getFullYear(), m.getMonth());
                if (prev) prev.title = '上個月';
                if (next) next.title = '下個月';
                break;
            }
            default: { // month
                const m = this.currentMonth;
                label.textContent = fmt(m.getFullYear(), m.getMonth());
                if (prev) prev.title = '上個月';
                if (next) next.title = '下個月';
            }
        }
    },

    changeMonth(delta) {
        switch (this.currentView) {
            case 'day':
                this.currentDay.setDate(this.currentDay.getDate() + delta);
                break;
            case 'week':
                this.currentWeekMonday.setDate(this.currentWeekMonday.getDate() + delta * 7);
                break;
            case 'year':
                this.currentYear += delta;
                this.currentMonth = new Date(this.currentYear, 0, 1);
                break;
            default:
                this.currentMonth.setMonth(this.currentMonth.getMonth() + delta);
        }
        this.loadCurrentView();
    },

    loadCurrentView() {
        this.updateNavLabel();
        switch (this.currentView) {
            case 'day':      return this._loadDayView();
            case 'week':     return this._loadWeekView();
            case 'year':     return this._loadYearView();
            case 'schedule': return this._loadScheduleView();
            default:         return this.loadMonth();
        }
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
                const isOvertimeShift = r.type === 'shift' && (r.note || '').includes('勞基法加班');
                const isCrossDay = r.type === 'shift' && r.start_time && r.end_time && r.end_time < r.start_time;
                let breakMatch = (r.note || '').match(/\(已扣除休息 (\d+(\.\d+)?)h\)/);
                let breakText = breakMatch ? ` (扣休 ${breakMatch[1]}h)` : '';
                
                let text = r.type === 'shift' ? `${r.start_time}${isCrossDay ? ' (+1日)' : ''}${breakText}` : `💰 獎金`;
                if (isHolidayShift) text += ' ×2';
                else if (isOvertimeShift) text += ' (加班)';
                
                const cColor = r.company_color || 'var(--text-secondary)';
                item.style.borderLeftColor = cColor;
                
                item.innerHTML = `<span style="font-weight: 500; letter-spacing: 0.3px;">${text}</span>`;
                
                if (r.type === 'bonus') {
                    item.style.color = '#fcd34d';
                    item.style.borderLeftColor = '#fcd34d';
                }
                else if (isHolidayShift) {
                    item.style.color = '#fca5a5';
                    item.style.borderLeftColor = '#fca5a5';
                }
                else if (isOvertimeShift) {
                    item.style.color = '#fde047';
                    item.style.borderLeftColor = '#fde047';
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

    // ─── Day View ────────────────────────────────────
    async _loadDayView() {
        const dateStr = this.formatDate(this.currentDay);
        const nextDay = new Date(this.currentDay); nextDay.setDate(nextDay.getDate() + 1);
        try {
            const [recRes, holRes] = await Promise.all([
                fetch(`/salary/api/records?start_date=${dateStr}&end_date=${this.formatDate(nextDay)}`),
                fetch(`/salary/api/holidays?year=${this.currentDay.getFullYear()}`)
            ]);
            this.records  = await recRes.json();
            this.holidays = holRes.ok ? await holRes.json() : {};
        } catch(e) { this.records = []; }
        this._renderDayView(dateStr);
        const start = new Date(this.currentDay);
        const end   = new Date(nextDay);
        this.updateMonthlySummary(start, end);
    },

    _renderDayView(dateStr) {
        const container = document.getElementById('dayViewBody');
        if (!container) return;
        const HOUR_H = window.innerWidth < 480 ? 30 : 40; // px per hour (smaller on mobile)
        const holidayName = (this.holidays||{})[dateStr];
        const dayRecords  = (this.records||[]).filter(r => r.date === dateStr && r.type === 'shift');
        const bonuses     = (this.records||[]).filter(r => r.date === dateStr && r.type === 'bonus');
        const todayStr    = this.formatDate(new Date());
        const isToday     = dateStr === todayStr;

        let html = `<div class="day-grid">`;
        // header row
        html += `<div></div><div class="week-col-header ${isToday?'today-col':''}" style="border-bottom:1px solid rgba(255,255,255,0.1);padding:8px 4px;">`;
        const d = this.currentDay;
        const DOW = ['日','一','二','三','四','五','六'];
        html += `週${DOW[d.getDay()]} <span class="wh-day-num">${d.getDate()}</span>`;
        if (holidayName) html += ` <span style="font-size:0.65rem;color:#fca5a5;">${holidayName}</span>`;
        html += `</div>`;

        for (let h = 0; h < 24; h++) {
            html += `<div class="week-time-col day-hour-row" style="height:${HOUR_H}px;">${h}:00</div>`;
            html += `<div class="day-col" data-date="${dateStr}" data-hour="${h}" style="height:${HOUR_H}px;"></div>`;
        }
        html += `</div>`;
        container.innerHTML = html;

        // Place event blocks
        dayRecords.forEach(r => {
            const [sh,sm] = (r.start_time||'00:00').split(':').map(Number);
            let   [eh,em] = (r.end_time||'00:00').split(':').map(Number);
            if (eh < sh) eh += 24; // cross-day
            const top    = (sm/60) * HOUR_H;
            const height = Math.max(((eh + em/60) - (sh + sm/60)) * HOUR_H, 20);
            const color  = r.company_color || '#38bdf8';
            const isHol  = holidayName;
            const block  = document.createElement('div');
            block.className = 'day-event-block';
            block.style.cssText = `top:${top}px;height:${height}px;background:${color}22;border-left:3px solid ${color};color:#fff;`;
            block.innerHTML = `<b>${r.start_time}–${r.end_time}</b>${isHol?' ×2':''}<br>${r.company_name||''} $${Math.round(r.amount)}`;
            block.onclick = (e) => { e.stopPropagation(); this.openEditModal(r); };
            const col = container.querySelector(`[data-date="${dateStr}"][data-hour="${sh}"]`);
            if (col) col.appendChild(block);
        });

        // Add bonus chips at top
        if (bonuses.length) {
            const firstCol = container.querySelector('[data-date]');
            if (firstCol) {
                bonuses.forEach(r => {
                    const chip = document.createElement('div');
                    chip.style.cssText = 'background:#fcd34d22;border-left:3px solid #fcd34d;border-radius:4px;padding:2px 6px;font-size:0.7rem;color:#fcd34d;cursor:pointer;margin:2px 4px;';
                    chip.textContent = `💰 獎金 $${Math.round(r.amount)}`;
                    chip.onclick = () => this.openEditModal(r);
                    firstCol.parentNode.insertBefore(chip, firstCol.nextSibling);
                });
            }
        }

        // Click empty cells to add
        container.querySelectorAll('.day-col').forEach(cell => {
            cell.addEventListener('click', () => {
                if (!this.isDateEditable(dateStr)) return;
                this.openAddModalForDate(new Date(this.currentDay));
            });
        });
    },

    // ─── Week View ────────────────────────────────────
    async _loadWeekView() {
        const mon = this.currentWeekMonday;
        const sun = new Date(mon); sun.setDate(sun.getDate() + 7);
        try {
            const [recRes, holRes] = await Promise.all([
                fetch(`/salary/api/records?start_date=${this.formatDate(mon)}&end_date=${this.formatDate(sun)}`),
                fetch(`/salary/api/holidays?year=${mon.getFullYear()}`)
            ]);
            this.records  = await recRes.json();
            this.holidays = holRes.ok ? await holRes.json() : {};
        } catch(e) { this.records = []; }
        this._renderWeekView();
        this.updateMonthlySummary(mon, sun);
    },

    _renderWeekView() {
        const container = document.getElementById('weekViewBody');
        if (!container) return;
        const HOUR_H  = window.innerWidth < 480 ? 26 : 36; // smaller on mobile
        const todayStr = this.formatDate(new Date());
        const DOW = ['日','一','二','三','四','五','六'];
        const days = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(this.currentWeekMonday);
            d.setDate(d.getDate() + i);
            days.push(d);
        }

        let html = `<div class="week-grid">`;
        // Time-col header placeholder
        html += `<div></div>`;
        days.forEach(d => {
            const ds  = this.formatDate(d);
            const hol = (this.holidays||{})[ds];
            const isT = ds === todayStr;
            html += `<div class="week-col-header ${isT?'today-col':''}">`;
            html += `週${DOW[d.getDay()]} <span class="wh-day-num">${d.getDate()}</span>`;
            if (hol) html += `<br><span style="font-size:0.55rem;color:#fca5a5;">${hol}</span>`;
            html += `</div>`;
        });

        // All-day bonus row
        html += `<div class="week-time-col" style="font-size:0.6rem;padding-top:4px;">全天</div>`;
        days.forEach(d => {
            const ds = this.formatDate(d);
            const bonuses = (this.records||[]).filter(r => r.date===ds && r.type==='bonus');
            html += `<div class="week-allday-row">`;
            bonuses.forEach(r => {
                html += `<span class="week-allday-chip" style="background:#fcd34d22;color:#fcd34d;" data-id="${r.id}">💰$${Math.round(r.amount)}</span>`;
            });
            html += `</div>`;
        });

        // Hour rows
        for (let h = 0; h < 24; h++) {
            html += `<div class="week-time-col week-hour-row" style="height:${HOUR_H}px;">${h}:00</div>`;
            days.forEach(d => {
                const ds = this.formatDate(d);
                html += `<div class="week-day-cell" data-date="${ds}" data-hour="${h}" style="height:${HOUR_H}px;"></div>`;
            });
        }
        html += `</div>`;
        container.innerHTML = html;

        // Place shift blocks
        (this.records||[]).filter(r => r.type==='shift').forEach(r => {
            const [sh,sm] = (r.start_time||'00:00').split(':').map(Number);
            let   [eh,em] = (r.end_time||'00:00').split(':').map(Number);
            if (eh < sh) eh += 24;
            const top    = (sm/60) * HOUR_H;
            const height = Math.max(((eh+em/60)-(sh+sm/60))*HOUR_H, 16);
            const color  = r.company_color || '#38bdf8';
            const isHol  = (this.holidays||{})[r.date];
            const block  = document.createElement('div');
            block.className = 'week-event-block';
            block.style.cssText = `top:${top}px;height:${height}px;background:${color}33;border-left:3px solid ${color};color:#fff;`;
            block.textContent = `${r.start_time}${isHol?' ×2':''}`;
            block.onclick = (e) => { e.stopPropagation(); this.openEditModal(r); };
            const cell = container.querySelector(`[data-date="${r.date}"][data-hour="${sh}"]`);
            if (cell) cell.appendChild(block);
        });

        // Bonus chips click
        container.querySelectorAll('[data-id]').forEach(chip => {
            const rid = parseInt(chip.dataset.id);
            const rec = (this.records||[]).find(r => r.id===rid);
            if (rec) chip.addEventListener('click', () => this.openEditModal(rec));
        });

        // Click empty cells to add
        container.querySelectorAll('.week-day-cell').forEach(cell => {
            cell.addEventListener('click', () => {
                const ds = cell.dataset.date;
                if (!this.isDateEditable(ds)) return;
                this.openAddModalForDate(new Date(ds + 'T00:00:00'));
            });
        });
    },

    // ─── Year View ────────────────────────────────────
    async _loadYearView() {
        const y = this.currentYear;
        try {
            const [recRes, holRes] = await Promise.all([
                fetch(`/salary/api/records?start_date=${y}-01-01&end_date=${y+1}-01-01`),
                fetch(`/salary/api/holidays?year=${y}`)
            ]);
            this.records  = await recRes.json();
            this.holidays = holRes.ok ? await holRes.json() : {};
        } catch(e) { this.records = []; }
        this._renderYearView();
        this.updateMonthlySummary(new Date(y,0,1), new Date(y+1,0,1));
    },

    _renderYearView() {
        const container = document.getElementById('yearViewBody');
        if (!container) return;
        const todayStr  = this.formatDate(new Date());
        const recordSet = new Set((this.records||[]).map(r => r.date));
        const DOW_SHORT = ['一','二','三','四','五','六','日'];

        let html = `<div class="year-grid">`;
        for (let m = 0; m < 12; m++) {
            html += `<div class="mini-month">`;
            html += `<div class="mini-month-title">${m+1}月</div>`;
            html += `<div class="mini-month-grid">`;
            DOW_SHORT.forEach(d => { html += `<div class="mini-dow">${d}</div>`; });

            const first = new Date(this.currentYear, m, 1);
            const start = new Date(first);
            start.setDate(1 - (first.getDay()||7) + 1);
            for (let i = 0; i < 42; i++) {
                const cur = new Date(start); cur.setDate(start.getDate()+i);
                const ds  = this.formatDate(cur);
                const otherMon = cur.getMonth() !== m;
                const isToday  = ds === todayStr;
                const hasRec   = recordSet.has(ds);
                let cls = 'mini-day';
                if (otherMon) cls += ' other-month-mini';
                else if (isToday) cls += ' today-mini';
                else if (hasRec) cls += ' has-record';
                html += `<div class="${cls}" data-date="${ds}" data-month="${m}">${cur.getDate()}</div>`;
            }
            html += `</div></div>`;
        }
        html += `</div>`;
        container.innerHTML = html;

        // Click mini-day → jump to day view
        container.querySelectorAll('.mini-day:not(.other-month-mini):not(.empty)').forEach(cell => {
            cell.addEventListener('click', () => {
                const ds = cell.dataset.date;
                if (!ds) return;
                const [y2,m2,d2] = ds.split('-').map(Number);
                this.currentDay = new Date(y2, m2-1, d2);
                this.currentMonth = new Date(y2, m2-1, 1);
                this.switchView('day');
            });
        });
    },

    // ─── Schedule (Agenda) View ───────────────────────
    async _loadScheduleView() {
        const y = this.currentMonth.getFullYear();
        const m = this.currentMonth.getMonth();
        const start = new Date(y, m, 1);
        const end   = new Date(y, m+1, 1);
        try {
            const [recRes, holRes] = await Promise.all([
                fetch(`/salary/api/records?start_date=${this.formatDate(start)}&end_date=${this.formatDate(end)}`),
                fetch(`/salary/api/holidays?year=${y}`)
            ]);
            this.records  = await recRes.json();
            this.holidays = holRes.ok ? await holRes.json() : {};
        } catch(e) { this.records = []; }
        this._renderScheduleView(start, end);
        this.updateMonthlySummary(start, end);
    },

    _renderScheduleView(start, end) {
        const container = document.getElementById('scheduleViewBody');
        if (!container) return;
        const todayStr = this.formatDate(new Date());
        const DOW = ['日','一','二','三','四','五','六'];
        const MONTH_ZH = ['一','二','三','四','五','六','七','八','九','十','十一','十二'];

        // Group records by date
        const grouped = {};
        (this.records||[]).forEach(r => {
            if (!grouped[r.date]) grouped[r.date] = [];
            grouped[r.date].push(r);
        });

        // Collect all dates in range with or without records
        const dates = [];
        for (let d = new Date(start); d < end; d.setDate(d.getDate()+1)) {
            dates.push(this.formatDate(new Date(d)));
        }

        // Only dates that have records (Agenda style)
        const activeDates = dates.filter(ds => grouped[ds] && grouped[ds].length > 0);

        if (activeDates.length === 0) {
            container.innerHTML = `<div class="schedule-empty">本月無排班紀錄 📅</div>`;
            return;
        }

        let html = '';
        activeDates.forEach(ds => {
            const dObj = new Date(ds + 'T00:00:00');
            const hol  = (this.holidays||{})[ds];
            const isT  = ds === todayStr;
            html += `<div class="schedule-date-group">`;
            html += `<div class="schedule-date-label ${isT?'sched-today':''} ${hol?'sched-holiday':''}"><span class="sched-day-num">${dObj.getDate()}</span>`;
            html += `${MONTH_ZH[dObj.getMonth()]}月 週${DOW[dObj.getDay()]}`;
            if (hol) html += ` 🎌 ${hol}`;
            html += `</div>`;

            (grouped[ds]||[]).sort((a,b) => (a.start_time||'').localeCompare(b.start_time||'')).forEach(r => {
                const color = r.company_color || (r.type==='bonus' ? '#fcd34d' : '#38bdf8');
                const timeStr = r.type==='shift'
                    ? `${r.start_time} – ${r.end_time}`
                    : '全天';
                const title = r.type==='shift'
                    ? `${r.company_name||'排班'} (${r.hours||0}h)`
                    : `💰 獎金${r.note ? ' – '+r.note : ''}`;
                html += `<div class="schedule-event-row" data-id="${r.id}">`;
                html += `<span class="sched-color-dot" style="background:${color};"></span>`;
                html += `<span class="sched-time">${timeStr}</span>`;
                html += `<span class="sched-title">${title}</span>`;
                html += `<span class="sched-amount">$${Math.round(r.amount)}</span>`;
                html += `</div>`;
            });
            html += `</div>`;
        });
        container.innerHTML = html;

        // Click rows to edit
        container.querySelectorAll('.schedule-event-row').forEach(row => {
            const rid = parseInt(row.dataset.id);
            const rec = (this.records||[]).find(r => r.id===rid);
            if (rec) row.addEventListener('click', () => this.openEditModal(rec));
        });
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
                    
                let badges = '';
                const noteStr = r.note || '';
                const isCrossDay = r.type === 'shift' && r.start_time && r.end_time && r.end_time < r.start_time;
                
                if (isCrossDay) {
                    badges += '<span style="background: rgba(139, 92, 246, 0.2); color: #c4b5fd; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px; display: inline-block; margin-bottom: 4px;">🌙 跨日班</span><br>';
                }
                if (noteStr.includes('國定假日')) {
                    badges += '<span style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px; display: inline-block; margin-bottom: 4px;">🏮 國定假日</span><br>';
                }
                if (noteStr.includes('勞基法加班')) {
                    badges += '<span style="background: rgba(245, 158, 11, 0.2); color: #fcd34d; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px; display: inline-block; margin-bottom: 4px;">🔥 勞基法加班</span><br>';
                }
                    
                tr.innerHTML = r.type === 'shift' ? `
                    <td>${r.date}</td><td>排班</td><td>${r.start_time} - ${r.end_time}<br>${companyHtml}</td><td>${r.hours}</td><td>${r.rate}/hr -> $${Math.round(r.amount)}</td><td>${badges}${r.note || ''}</td>
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
