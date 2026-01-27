const downloaderApp = {
    currentVideo: null,
    activeDownloadId: null,
    pollInterval: null,

    init() {
        this.bindEvents();
        this.refreshFiles();
    },

    bindEvents() {
        document.getElementById('previewBtn').addEventListener('click', () => this.previewVideo());
        document.getElementById('downloadBtn').addEventListener('click', () => this.startDownload());
        document.getElementById('refreshFilesBtn').addEventListener('click', () => this.refreshFiles());
        document.getElementById('openFolderBtn').addEventListener('click', () => this.openFolder());

        // Enter key on input
        document.getElementById('urlInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.previewVideo();
        });
    },

    async previewVideo() {
        const url = document.getElementById('urlInput').value.trim();
        if (!url) return;

        const btn = document.getElementById('previewBtn');
        btn.disabled = true;
        btn.textContent = '載入中...';
        document.getElementById('videoInfoCard').classList.add('hidden');

        try {
            const res = await fetch('/download/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            if (res.ok) {
                const info = await res.json();
                this.currentVideo = info;
                this.renderVideoInfo(info);
                document.getElementById('downloadBtn').disabled = false;
            } else {
                alert('無法獲取影片資訊，請檢查網址');
                this.currentVideo = null;
                document.getElementById('downloadBtn').disabled = true;
            }
        } catch (error) {
            console.error(error);
            alert('網路錯誤');
        } finally {
            btn.disabled = false;
            btn.textContent = '🔍 預覽';
        }
    },

    renderVideoInfo(info) {
        document.getElementById('videoThumb').src = info.thumbnail;
        document.getElementById('videoTitle').textContent = info.title;
        document.getElementById('videoAuthor').textContent = info.uploader;

        // Format duration
        const h = Math.floor(info.duration / 3600);
        const m = Math.floor((info.duration % 3600) / 60);
        const s = info.duration % 60;
        const durStr = h > 0 ? `${h}:${m}:${s}` : `${m}:${s}`;
        document.getElementById('videoDuration').textContent = `時長: ${durStr}`;

        document.getElementById('videoInfoCard').classList.remove('hidden');
    },

    async startDownload() {
        if (!this.currentVideo) return;

        const url = document.getElementById('urlInput').value.trim();
        const format = document.querySelector('input[name="format"]:checked').value;
        const subtitles = document.getElementById('subtitles').checked;
        const embedSubtitles = document.getElementById('embedSubtitles').checked;

        const options = {
            format: format,
            subtitles: subtitles,
            embed_subtitles: embedSubtitles,
            title: this.currentVideo.title
        };

        const btn = document.getElementById('downloadBtn');
        btn.disabled = true;

        try {
            const res = await fetch('/download/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, options: options })
            });

            if (res.ok) {
                const data = await res.json();
                this.activeDownloadId = data.id;
                this.startPolling();
            } else {
                alert('下載啟動失敗');
                btn.disabled = false;
            }
        } catch (error) {
            console.error(error);
            btn.disabled = false;
        }
    },

    startPolling() {
        if (this.pollInterval) clearInterval(this.pollInterval);

        this.pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/download/api/status/${this.activeDownloadId}`);
                if (res.ok) {
                    const status = await res.json();
                    this.updateProgress(status);

                    if (status.status === 'completed' || status.status === 'error') {
                        clearInterval(this.pollInterval);
                        document.getElementById('downloadBtn').disabled = false;
                        if (status.status === 'completed') {
                            this.refreshFiles();
                            // Optional: clear completed tasks on server
                            fetch('/download/api/cleanup', { method: 'POST' });
                        }
                    }
                }
            } catch (error) {
                console.error(error);
            }
        }, 1000);
    },

    updateProgress(status) {
        const bar = document.getElementById('mainProgress');
        const text = document.getElementById('statusText');
        const speed = document.getElementById('speedStat');
        const eta = document.getElementById('etaStat');

        bar.style.width = `${status.progress}%`;

        if (status.status === 'downloading') {
            text.textContent = `下載中... ${status.progress.toFixed(1)}%`;
            speed.textContent = `速度: ${status.speed}`;
            eta.textContent = `剩餘時間: ${status.eta}`;
        } else if (status.status === 'processing') {
            text.textContent = '處理中... (轉檔/合併)';
        } else if (status.status === 'completed') {
            text.textContent = '✅ 下載完成';
            bar.style.backgroundColor = '#2ed573';
        } else if (status.status === 'error') {
            text.textContent = `❌ 錯誤: ${status.error}`;
            bar.style.backgroundColor = '#ff6b6b';
        }
    },

    async refreshFiles() {
        try {
            const res = await fetch('/download/api/files');
            const files = await res.json();

            const list = document.getElementById('filesList');
            list.innerHTML = '';

            if (files.length === 0) {
                list.innerHTML = '<div style="padding:10px;text-align:center;color:#666">暫無檔案</div>';
                return;
            }

            files.forEach(file => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-info">
                        <span class="file-name" title="${file.name}">${file.name}</span>
                        <span class="file-meta">${file.size}</span>
                    </div>
                    <div class="file-actions">
                        <a href="/download/api/files/download/${encodeURIComponent(file.name)}" class="btn-icon download" title="下載到設備">
                            📥
                        </a>
                        <button class="btn-delete" onclick="downloaderApp.deleteFile('${file.name}')" title="刪除檔案">🗑️</button>
                    </div>
                `;
                list.appendChild(item);
            });
        } catch (error) {
            console.error(error);
        }
    },

    async deleteFile(filename) {
        if (!confirm(`確定要刪除 ${filename} 嗎？`)) return;

        try {
            const res = await fetch(`/download/api/files/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                this.refreshFiles();
            }
        } catch (error) {
            console.error(error);
        }
    },

    async openFolder() {
        await fetch('/download/api/open_folder', { method: 'POST' });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    downloaderApp.init();
});
