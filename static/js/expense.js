const expenseApp = {
    currentPeriod: { start: null, end: null },
    records: [],
    monthlyBudget: 10000,

    // Initializers
    init() {
        const dashboard = document.querySelector('.expense-dashboard');
        this.currentPeriod.start = dashboard.dataset.startDate;
        this.currentPeriod.end = dashboard.dataset.endDate;

        this.bindEvents();
        this.loadSettings().then(() => this.loadData());
    },

    initHistory() {
        this.bindEvents();
        const select = document.getElementById('periodSelect');
        if (select) select.addEventListener('change', () => this.loadHistoryData());
        this.loadHistoryPeriods();
    },

    initSettings() {
        const form = document.getElementById('settingsForm');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());

                try {
                    const res = await fetch('/expense/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    if (res.ok) alert('設定已儲存');
                } catch (error) {
                    console.error(error);
                }
            });
        }
    },

    // Core Logic
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

        // Quick Tags Logic
        document.querySelectorAll('.tag-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const noteInput = document.getElementById('expenseNote');
                const categorySelect = document.getElementById('expenseCategory');
                if (noteInput) noteInput.value = pill.dataset.value;
                if (categorySelect) categorySelect.value = '飲食';
            });
        });

        // Outside click close
        window.onclick = (e) => {
            if (e.target.classList.contains('modal')) this.closeModal();
        };

        // Esc key close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
        });
    },

    async loadSettings() {
        try {
            const res = await fetch('/expense/api/settings');
            const data = await res.json();
            this.monthlyBudget = data.monthly_budget;
        } catch (error) {
            console.error(error);
        }
    },

    async loadData() {
        const url = `/expense/api/records?start_date=${this.currentPeriod.start}&end_date=${this.currentPeriod.end}`;
        try {
            const res = await fetch(url);
            const data = await res.json();
            this.records = data.records;
            this.renderSummary(data.total_amount);
            this.renderList('expenseList');

            const display = document.getElementById('periodDisplay');
            if (display) display.textContent = `${data.period.start} ~ ${data.period.end}`;
        } catch (error) {
            console.error('Error loading expenses:', error);
        }
    },

    async loadHistoryPeriods() {
        try {
            const res = await fetch('/expense/api/history/periods');
            const periods = await res.json();
            const select = document.getElementById('periodSelect');
            select.innerHTML = '';

            periods.reverse().forEach(p => {
                const opt = document.createElement('option');
                opt.value = `${p.start},${p.end}`;
                opt.textContent = p.label;
                select.appendChild(opt);
            });

            // Auto trigger first load
            if (select.value) this.loadHistoryData();
        } catch (error) {
            console.error(error);
        }
    },

    async loadHistoryData() {
        const select = document.getElementById('periodSelect');
        const [start, end] = select.value.split(',');
        const url = `/expense/api/records?start_date=${start}&end_date=${end}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            this.records = data.records;

            // Update Mini Summary in History
            const histTotal = document.getElementById('historyTotal');
            if (histTotal) histTotal.textContent = `$${Math.round(data.total_amount).toLocaleString()}`;

            const histCount = document.getElementById('historyCount');
            if (histCount) histCount.textContent = data.records.length;

            this.renderList('historyExpenseList');
        } catch (error) {
            console.error(error);
        }
    },

    renderSummary(total) {
        const el = document.getElementById('totalExpense');
        if (!el) return;

        el.textContent = `$${Math.round(total).toLocaleString()}`;
        const remaining = Math.max(0, this.monthlyBudget - total);
        document.getElementById('remainingBudget').textContent = `$${Math.round(remaining).toLocaleString()}`;

        const percent = Math.min(100, (total / this.monthlyBudget) * 100);
        const progressFill = document.getElementById('budgetProgress');
        progressFill.style.width = `${percent}%`;

        if (percent > 90) progressFill.style.background = 'linear-gradient(90deg, #ff4d4d, #f9ca24)';
        else if (percent > 70) progressFill.style.background = 'linear-gradient(90deg, #f0932b, #ffbe76)';
        else progressFill.style.background = 'linear-gradient(90deg, #4ecdc4, #abe9cd)';
    },

    renderList(containerID) {
        const container = document.getElementById(containerID);
        if (!container) return;

        if (this.records.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="text-align:center; padding:50px 20px; color:var(--text-secondary)">
                    <span class="material-icons" style="font-size: 3rem; margin-bottom: 15px; display: block; opacity: 0.5">receipt_long</span>
                    <p>本期尚無紀錄</p>
                </div>`;
            return;
        }

        const colorMap = {
            '飲食': 'var(--cat-food)',
            '衣著': 'var(--cat-clothing)',
            '居住': 'var(--cat-housing)',
            '交通': 'var(--cat-transport)',
            '教育': 'var(--cat-edu)',
            '娛樂': 'var(--cat-play)',
            '其他': 'var(--cat-other)'
        };

        container.innerHTML = '';
        this.records.forEach(r => {
            const item = document.createElement('div');
            item.className = 'expense-item';
            item.onclick = () => this.openEditModal(r);

            const categoryEmoji = r.category ? r.category.split(' ')[0] : '📦';
            const categoryName = r.category ? (r.category.includes(' ') ? r.category.split(' ')[1] : r.category) : '其他';
            const catColor = colorMap[categoryName] || 'var(--cat-other)';

            const timePart = r.timestamp.split(' ')[1].substring(0, 5);
            const datePart = r.timestamp.split(' ')[0].substring(5).replace('-', '/');

            item.innerHTML = `
                <div class="expense-item-left">
                    <div class="category-icon-wrapper" style="background: ${catColor}20; color: ${catColor}">
                        ${categoryEmoji}
                    </div>
                    <div class="expense-details">
                        <span class="expense-name">${r.note}</span>
                        <div class="expense-meta">
                            <span>${datePart} ${timePart}</span>
                            <span class="dot"></span>
                            <span>${categoryName}</span>
                        </div>
                    </div>
                </div>
                <div class="expense-amount" style="color: ${catColor}">$${Math.round(r.amount).toLocaleString()}</div>
            `;
            container.appendChild(item);
        });
    },

    // Modal Handling
    openAddModal() {
        this.resetForm();
        const now = new Date();
        const timezoneOffset = now.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(now - timezoneOffset)).toISOString().slice(0, 16);

        document.getElementById('expenseTimestamp').value = localISOTime;
        document.getElementById('modalTitle').textContent = '新增支出';
        document.getElementById('deleteExpenseBtn').classList.add('hidden');
        document.getElementById('expenseModal').classList.add('show');
    },

    openEditModal(record) {
        this.resetForm();
        document.getElementById('expenseId').value = record.id;
        document.getElementById('expenseNote').value = record.note;
        document.getElementById('expenseAmount').value = record.amount;

        const catName = record.category ? (record.category.includes(' ') ? record.category.split(' ')[1] : record.category) : '其他';
        document.getElementById('expenseCategory').value = catName;

        const ts = record.timestamp.replace(' ', 'T').substring(0, 16);
        document.getElementById('expenseTimestamp').value = ts;

        document.getElementById('modalTitle').textContent = '編輯紀錄';
        document.getElementById('deleteExpenseBtn').classList.remove('hidden');
        document.getElementById('expenseModal').classList.add('show');
    },

    closeModal() {
        const modal = document.getElementById('expenseModal');
        if (modal) modal.classList.remove('show');
    },

    resetForm() {
        const form = document.getElementById('expenseForm');
        if (form) {
            form.reset();
            document.getElementById('expenseId').value = '';
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        data.timestamp = data.timestamp.replace('T', ' ') + ':00';

        const id = data.id;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/expense/api/records/${id}` : '/expense/api/records';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                this.closeModal();
                // Smart Refresh
                if (document.querySelector('.expense-dashboard')) this.loadData();
                else if (document.querySelector('.expense-history')) this.loadHistoryData();
            } else {
                alert('儲存失敗');
            }
        } catch (error) {
            console.error(error);
        }
    },

    async deleteCurrentRecord() {
        if (!confirm('確定要刪除這筆紀錄嗎？')) return;
        const id = document.getElementById('expenseId').value;
        try {
            const res = await fetch(`/expense/api/records/${id}`, { method: 'DELETE' });
            if (res.ok) {
                this.closeModal();
                if (document.querySelector('.expense-dashboard')) this.loadData();
                else if (document.querySelector('.expense-history')) this.loadHistoryData();
            }
        } catch (error) {
            console.error(error);
        }
    },

    changePeriod(delta) {
        const currentStart = new Date(this.currentPeriod.start);
        currentStart.setMonth(currentStart.getMonth() + delta);
        const nextMonth = new Date(currentStart);
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        this.currentPeriod.start = this.formatDate(currentStart);
        this.currentPeriod.end = this.formatDate(nextMonth);
        this.loadData();
    },

    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.expense-dashboard')) expenseApp.init();
    else if (document.querySelector('.expense-history')) expenseApp.initHistory();
    else if (document.querySelector('.expense-settings')) expenseApp.initSettings();
});
