from flask import Blueprint, render_template, request, jsonify
from services.download_service import DownloadManager

download_bp = Blueprint('download', __name__)
manager = DownloadManager()

@download_bp.route('/')
def index():
    return render_template('downloader/index.html')

@download_bp.route('/api/validate', methods=['POST'])
def validate():
    url = request.json.get('url')
    is_valid = manager.validate_url(url)
    return jsonify({'valid': is_valid})

@download_bp.route('/api/info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    info = manager.get_video_info(url)
    if info:
        return jsonify(info)
    return jsonify({'error': 'Could not get video info'}), 400

@download_bp.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    options = data.get('options', {})
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
        
    download_id = manager.start_download(url, options)
    return jsonify({'id': download_id, 'status': 'started'})

@download_bp.route('/api/status/<download_id>')
def get_status(download_id):
    status = manager.get_status(download_id)
    if status:
        return jsonify(status)
    return jsonify({'error': 'Download not found'}), 404

@download_bp.route('/api/tasks')
def get_all_tasks():
    return jsonify(manager.get_all_downloads())

@download_bp.route('/api/files')
def list_files():
    return jsonify(manager.list_local_files())

@download_bp.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    if manager.delete_file(filename):
        return jsonify({'success': True})
    return jsonify({'error': 'File not found'}), 404

@download_bp.route('/api/files/download/<filename>')
def download_file_to_browser(filename):
    from flask import send_from_directory
    from config import Config
    import os
    
    directory = Config.DOWNLOAD_PATH
    # Ensure file exists
    if os.path.exists(os.path.join(directory, filename)):
        return send_from_directory(directory, filename, as_attachment=True)
    return "File not found", 404

@download_bp.route('/api/open_folder', methods=['POST'])
def open_folder():
    if manager.open_folder():
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to open folder'}), 500

@download_bp.route('/api/cleanup', methods=['POST'])
def cleanup():
    manager.clear_completed()
    return jsonify({'success': True})
