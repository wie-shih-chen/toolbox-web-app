from flask import Blueprint, redirect
import os

download_bp = Blueprint('download', __name__)

@download_bp.route('/')
@download_bp.route('/<path:path>')
def index(path=None):
    # Redirect to the Render URL
    # We can use an environment variable or a hardcoded URL.
    # Since the user just set it up, let's use a placeholder or ask them to set env.
    render_url = os.environ.get('RENDER_DOWNLOADER_URL', 'https://yt1s.ltd/zh-tw214nb/youtube-to-mp4') 
    return redirect(render_url)
