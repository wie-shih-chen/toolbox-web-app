import os
import threading
import uuid
import logging
from datetime import datetime
from yt_dlp import YoutubeDL
import re
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.download_history = []
        self.download_path = Config.DOWNLOAD_PATH
        
    def validate_url(self, url):
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return youtube_regex.match(url) is not None

    def get_video_info(self, url):
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "nocheckcertificate": True,
            "noplaylist": True,
            "forcejson": True,
            "no_warnings": True,
            "socket_timeout": 10,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'id': info.get('id')
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None

    def start_download(self, url, options):
        download_id = str(uuid.uuid4())
        
        # Determine format options
        ydl_opts = {
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: self._progress_hook(download_id, d)],
            'nocheckcertificate': True,
        }
        
        format_type = options.get('format', 'mp4_720p')
        
        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif format_type == 'mp4_1080p':
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        elif format_type == 'mp4_720p':
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        else: # 480p and others
            ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]'

        # Subtitles
        if options.get('subtitles'):
            ydl_opts.update({
                'writesubtitles': True,
                'subtitleslangs': options.get('subtitle_langs', ['zh-TW', 'en', 'zh']),
            })
            if options.get('embed_subtitles'):
                ydl_opts['embedsubtitles'] = True

        # Initial Status
        self.active_downloads[download_id] = {
            'id': download_id,
            'url': url,
            'title': options.get('title', 'Downloading...'),
            'status': 'starting',
            'progress': 0,
            'speed': '0 MiB/s',
            'eta': 'Unknown',
            'filename': '',
            'error': None
        }

        # Start Thread
        thread = threading.Thread(target=self._download_worker, args=(download_id, url, ydl_opts))
        thread.start()
        
        return download_id

    def _download_worker(self, download_id, url, ydl_opts):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if download_id in self.active_downloads:
                self.active_downloads[download_id]['status'] = 'completed'
                self.active_downloads[download_id]['progress'] = 100
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            if download_id in self.active_downloads:
                self.active_downloads[download_id]['status'] = 'error'
                self.active_downloads[download_id]['error'] = str(e)

    def _progress_hook(self, download_id, d):
        if d['status'] == 'downloading':
            if download_id in self.active_downloads:
                # Calculate progress
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                progress = (downloaded / total * 100) if total > 0 else 0
                
                self.active_downloads[download_id].update({
                    'status': 'downloading',
                    'progress': progress,
                    'speed': d.get('_speed_str', 'N/A'),
                    'eta': d.get('_eta_str', 'N/A'),
                    'filename': d.get('filename', '')
                })
        elif d['status'] == 'finished':
            if download_id in self.active_downloads:
                self.active_downloads[download_id].update({
                    'status': 'processing', # Post-processing (ffmpeg etc)
                    'progress': 99,
                    'filename': d.get('filename', '')
                })

    def get_status(self, download_id):
        return self.active_downloads.get(download_id)

    def get_all_downloads(self):
        return list(self.active_downloads.values())

    def clear_completed(self):
        # Remove completed or error tasks
        to_remove = []
        for did, task in self.active_downloads.items():
            if task['status'] in ['completed', 'error']:
                to_remove.append(did)
        
        for did in to_remove:
            del self.active_downloads[did]
            
    def list_local_files(self):
        files = []
        if os.path.exists(self.download_path):
            for f in os.listdir(self.download_path):
                if not f.startswith('.'):
                    path = os.path.join(self.download_path, f)
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        files.append({
                            'name': f,
                            'size': self._format_size(size),
                            'path': path
                        })
        return files

    def _format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def delete_file(self, filename):
        path = os.path.join(self.download_path, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
        
    def open_folder(self):
        import subprocess
        try:
            subprocess.Popen(["open", self.download_path])
            return True
        except:
            return False

