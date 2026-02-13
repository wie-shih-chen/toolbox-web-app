// Auto-save for Settings Page
const settingsAutoSave = {
    saveTimeout: null,

    init() {
        // Auto-save for profile and notification settings
        const emailInput = document.getElementById('email');
        const notificationInputs = document.querySelectorAll('input[name="notification_methods"]');
        const reportDaySelect = document.querySelector('select[name="monthly_report_day"]');

        if (emailInput) {
            emailInput.addEventListener('input', () => this.debouncedSave('email'));
        }

        if (notificationInputs.length > 0) {
            notificationInputs.forEach(input => {
                input.addEventListener('change', () => this.debouncedSave('notifications'));
            });
        }

        if (reportDaySelect) {
            reportDaySelect.addEventListener('change', () => this.debouncedSave('notifications'));
        }
    },

    debouncedSave(type) {
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            if (type === 'email') {
                this.saveEmail();
            } else if (type === 'notifications') {
                this.saveNotifications();
            }
        }, 800); // Wait 800ms after last input
    },

    async saveEmail() {
        const emailInput = document.getElementById('email');
        if (!emailInput) return;

        try {
            const res = await fetch('/auth/api/update_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: emailInput.value })
            });

            if (res.ok) {
                this.showToast('✅ Email 已自動儲存', 'success');
            } else {
                const data = await res.json();
                this.showToast('❌ ' + (data.error || '儲存失敗'), 'error');
            }
        } catch (e) {
            console.error(e);
        }
    },

    async saveNotifications() {
        const methods = Array.from(document.querySelectorAll('input[name="notification_methods"]:checked'))
            .map(input => input.value);

        const reportDay = document.querySelector('select[name="monthly_report_day"]')?.value || 5;

        try {
            const res = await fetch('/auth/api/update_notifications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    notification_methods: methods,
                    monthly_report_day: parseInt(reportDay)
                })
            });

            if (res.ok) {
                this.showToast('✅ 通知設定已儲存', 'success');
            } else {
                this.showToast('❌ 儲存失敗', 'error');
            }
        } catch (e) {
            console.error(e);
        }
    },

    showToast(message, type) {
        const existingToast = document.getElementById('autoSaveToast');
        if (existingToast) existingToast.remove();

        const toast = document.createElement('div');
        toast.id = 'autoSaveToast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'success' ? 'rgba(34, 197, 94, 0.95)' : 'rgba(239, 68, 68, 0.95)'};
            color: white;
            padding: 14px 24px;
            border-radius: 10px;
            font-size: 0.95rem;
            z-index: 10000;
            box-shadow: 0 6px 16px rgba(0,0,0,0.3);
            animation: slideDown 0.3s ease;
            font-weight: 500;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.settings-wrapper')) {
        settingsAutoSave.init();
    }
});
